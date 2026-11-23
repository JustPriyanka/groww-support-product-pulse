from core.intents import classify

def test_rephrasings_same_intent():
    qs = ["Why was a DP charge deducted when I sold my shares?", "what is this depository fee taken when selling stocks",
          "charges on selling not shown before order", "Are DP charges per stock or per order?"]
    assert {classify(q).intent for q in qs} == {"dp_charges"}

def test_scheme_and_fee():
    r = classify("Is there an exit load on HDFC Mid Cap Fund if I redeem in 6 months?")
    assert (r.intent, r.fee_type, r.scheme) == ("exit_load", "exit_load", "hdfc_mid_cap")

def test_voice_command_blocked():
    assert classify("approve the pulse email").intent == "voice_command_blocked"
