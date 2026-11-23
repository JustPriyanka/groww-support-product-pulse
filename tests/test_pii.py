import hashlib, uuid
import pytest
from core.pii import contains_pii, redact

POSITIVE = [
    ("My PAN is ABCPK1234D", "PAN"), ("pan: abcpk1234d", "PAN"),
    ("aadhaar 2345 6789 0123", "AADHAAR"), ("aadhaar 2345-6789-0123", "AADHAAR"), ("234567890123", "AADHAAR"),
    ("call +91 98765 43210", "PHONE"), ("9876543210", "PHONE"), ("+91-9876543210", "PHONE"),
    ("mail a.b@gmail.com", "EMAIL"), ("OTP is 482913", "OTP"), ("my otp: 4829", "OTP"),
    ("account no 123456789012", "ACCOUNT_NUMBER"), ("A/c 5551234", "ACCOUNT_NUMBER"),
    ("folio number 12345678/90", "ACCOUNT_NUMBER"), ("client id 8ABCD123", "ACCOUNT_NUMBER"),
    ("card 4111 1111 1111 1111", "CARD"), ("ifsc HDFC0001234", "IFSC"), ("upi rahul@okhdfc", "UPI_ID"),
    ("my name is Rahul Sharma", "PERSON_NAME"),
    # labelled but malformed (voice transcription): Q32 leaked "My PAN number is AYOPB57069"
    ("My PAN number is AYOPB57069", "PAN"), ("pan card no: ABCP1234", "PAN"),
    ("aadhaar number is 2345 6789 012", "AADHAAR"), ("my account number is 5551234", "ACCOUNT_NUMBER"),
]
NEGATIVE = [
    "exit load of 1% if redeemed within 365 days", "paid ₹1,26,000 for 154 shares", "charged Rs 20 per order",
    "I am unable to withdraw since 2024", "my account is blocked", "Nifty 50 Index Fund expense ratio 0.20%",
    "https://groww.in/help/x/what-are-dp-charges-depository-participant-charges-1", "order--86",
    "my PAN is linked but KYC failed", "Pan India coverage since 2024", "aadhaar linking failed twice",
]

@pytest.mark.parametrize("text,kind", POSITIVE)
def test_detects(text, kind):
    r = redact(text)
    assert kind in r.found
    assert f"[{kind}_REDACTED]" in r.text

@pytest.mark.parametrize("text", NEGATIVE)
def test_no_false_positive(text):
    assert contains_pii(text) == []

def test_hashes_and_uuids_are_not_pii():
    assert not any(contains_pii(hashlib.sha256(str(i).encode()).hexdigest()) for i in range(5000))
    assert not any(contains_pii(str(uuid.uuid4())) for _ in range(5000))

def test_redacted_output_is_clean():
    r = redact("PAN ABCPK1234D phone 9876543210 acct 123456789012 otp 1234")
    assert contains_pii(r.text) == []


def test_startup_scrub_rewrites_rows_written_before_a_detector_fix(tmp_path, monkeypatch):
    import sqlite3
    from core import db
    monkeypatch.setattr(db, "APP_DB", tmp_path / "app.db")
    monkeypatch.setattr(db, "_conn_singleton", None)
    db.init_db()
    # simulate a row stored before the labelled-PAN pattern existed (bypasses the write guard)
    with db.tx() as c:
        c.execute("INSERT INTO questions (created_at, channel, text_redacted, status) VALUES ('t','voice',?,'ready')",
                  ["My PAN number is AYOPB57069."])
    assert db.scrub_pii() == 1
    assert db.one("SELECT text_redacted FROM questions")["text_redacted"] == "My PAN number is [PAN_REDACTED]."
    assert db.scrub_pii() == 0
