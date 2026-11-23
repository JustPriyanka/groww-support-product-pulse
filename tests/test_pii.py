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
]
NEGATIVE = [
    "exit load of 1% if redeemed within 365 days", "paid ₹1,26,000 for 154 shares", "charged Rs 20 per order",
    "I am unable to withdraw since 2024", "my account is blocked", "Nifty 50 Index Fund expense ratio 0.20%",
    "https://groww.in/help/x/what-are-dp-charges-depository-participant-charges-1", "order--86",
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
