import email
import email.utils
import imaplib
import os
import re
import time

CODE_PATTERN = re.compile(r"(\d{6})\s+est votre code")


def mail_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", "ignore")
        return ""
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", "ignore")


def extract_code(body):
    found = CODE_PATTERN.search(body)
    return found.group(1) if found else None


def is_fresh(msg, since_ts, tolerance=30):
    sent = email.utils.parsedate_to_datetime(msg["Date"]).timestamp()
    return sent >= since_ts - tolerance


def get_code(since_ts, timeout=120, poll=5):
    deadline = time.time() + timeout
    sender = os.environ.get("MPD_MAIL_SENDER", "no-reply@people-doc.com")
    while time.time() < deadline:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        try:
            imap.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"].replace(" ", ""))
            imap.select("INBOX")
            _, data = imap.search(None, f'(FROM "{sender}" UNSEEN)')
            for mid in reversed(data[0].split()):
                _, raw = imap.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(raw[0][1])
                if not is_fresh(msg, since_ts):
                    continue
                code = extract_code(mail_body(msg))
                if code:
                    return code
        finally:
            try:
                imap.logout()
            except Exception:
                pass
        time.sleep(poll)
    raise RuntimeError("code de verification non recu")
