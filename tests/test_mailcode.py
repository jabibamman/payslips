import email
import sys
import time
from email.utils import format_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mailcode import extract_code, is_fresh, mail_body


def build(body, sent):
    msg = email.message_from_string(
        f"From: no-reply@people-doc.com\nDate: {format_datetime(sent)}\n"
        "Content-Type: text/plain; charset=utf-8\n\n" + body
    )
    return msg


def test_extract_code_from_real_mail_body():
    body = "242069 est votre code de vérification MyPeopleDoc.\n-----\nBesoin d'aide ?"
    assert extract_code(body) == "242069"


def test_extract_code_returns_none_without_code():
    assert extract_code("Vous avez un nouveau document") is None
    assert extract_code("12345 est votre code") is None


def test_freshness_filters_old_codes():
    now = datetime.now(timezone.utc)
    fresh = build("123456 est votre code", now)
    old = build("123456 est votre code", now - timedelta(hours=2))
    assert mail_body(fresh).startswith("123456")
    assert is_fresh(fresh, time.time())
    assert not is_fresh(old, time.time())
