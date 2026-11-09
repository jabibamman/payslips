import os
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

from mailcode import get_code
from payslip_meta import dest_parts, employer_from

BASE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(os.environ.get("OUT_DIR", BASE / "out"))
STATE = pathlib.Path(os.environ.get("STATE_FILE", BASE / "state.json"))
DEBUG = pathlib.Path(os.environ.get("DEBUG_DIR", BASE / "debug"))
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
MAX_DOCS = int(os.environ.get("MAX_DOCS", "0"))
DOC_FILTER = os.environ.get("DOC_FILTER", "bulletin").lower()
PREFIX = os.environ.get("PAYSLIP_PREFIX", "Bulletin")
SUBDIR = os.environ.get("PAYSLIP_SUBDIR", "Bulletins de paye")
URL = os.environ.get("MPD_URL", "https://www.mypeopledoc.com/")
BASE_URL = URL.split("#")[0].rstrip("/")

SEL_EMAIL = os.environ.get("SEL_EMAIL", "#username")
SEL_PASSWORD = os.environ.get("SEL_PASSWORD", "#password")
SEL_SUBMIT = os.environ.get("SEL_SUBMIT", "button[type=submit]:not([disabled])")
SEL_OTP = os.environ.get("SEL_OTP", "[data-test-input-2fa-code]")
SEL_ROW = os.environ.get("SEL_ROW", "[data-test-document-list-item]")

OUT.mkdir(parents=True, exist_ok=True)
DEBUG.mkdir(parents=True, exist_ok=True)


def shot(page, name):
    page.screenshot(path=str(DEBUG / f"{name}.png"), full_page=True)


def load_all(page):
    """La liste est paginee (defilement infini) : on descend jusqu'a stabilisation."""
    last = -1
    for _ in range(50):
        n = page.locator(SEL_ROW).count()
        if n == last:
            break
        last = n
        page.mouse.wheel(0, 20000)
        page.locator(SEL_ROW).last.scroll_into_view_if_needed()
        page.wait_for_timeout(1500)


def login(page):
    page.goto(URL)
    page.wait_for_selector(SEL_EMAIL)
    page.locator(SEL_EMAIL).press_sequentially(os.environ["MPD_EMAIL"], delay=20)
    page.locator(SEL_PASSWORD).press_sequentially(os.environ["MPD_PASSWORD"], delay=20)
    started = time.time()
    page.click(SEL_SUBMIT)
    page.wait_for_timeout(3000)
    shot(page, "after-password")
    otp = page.locator(SEL_OTP)
    if otp.count():
        otp.first.press_sequentially(get_code(started), delay=20)
        # "Ne plus demander de code pendant 60 jours sur cet appareil"
        page.locator("[data-test-input-trusted-device-2fa]").check()
        page.click(SEL_SUBMIT)
        page.wait_for_url(lambda u: "/2fa/" not in u, timeout=30000)
    page.wait_for_load_state("networkidle")
    shot(page, "after-login")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=["--no-sandbox"])
        ctx = browser.new_context(storage_state=str(STATE)) if STATE.exists() else browser.new_context()
        page = ctx.new_page()
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        if page.locator(SEL_EMAIL).count():
            login(page)
        ctx.storage_state(path=str(STATE))
        os.chmod(STATE, 0o600)
        shot(page, "documents")
        page.wait_for_selector(SEL_ROW)
        if not MAX_DOCS:
            load_all(page)
        docs = page.eval_on_selector_all(
            SEL_ROW,
            "els => els.map(e => [e.getAttribute('data-test-document-list-item'), e.innerText])",
        )
        docs = [(i, t) for i, t in docs if DOC_FILTER in t.lower()]
        if not docs:
            raise RuntimeError("aucun bulletin trouve (session expiree ou site modifie ?)")
        limit = min(len(docs), MAX_DOCS) if MAX_DOCS else len(docs)
        print(f"{len(docs)} bulletins trouves, {limit} traites")
        new = 0
        for doc_id, text in docs[:limit]:
            title = text.strip().split("\n")[0]  # pas la ligne "Document date du..." (mois suivant)
            folder, name = dest_parts(title, SUBDIR, prefix=employer_from(text, PREFIX))
            target = OUT / folder / name
            if target.exists():
                continue
            resp = ctx.request.get(f"{BASE_URL}/api/documents/{doc_id}/download")
            body = resp.body()
            if not resp.ok or not body.startswith(b"%PDF"):
                raise RuntimeError(f"telechargement invalide pour {name} (HTTP {resp.status})")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            new += 1
            print(f"telecharge: {folder}/{name}")
        print(f"{new} nouveaux fichiers")
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"echec: {exc}", file=sys.stderr)
        sys.exit(1)
