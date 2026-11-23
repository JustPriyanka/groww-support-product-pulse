from core.policy import (detect_advice_request, detect_performance_request, find_advice, find_performance,
                         numbers_in, split_sentences)

def test_advice_requests():
    for q in ["Should I buy HDFC Small Cap?", "Which fund is best for SIP", "is hdfc flexi cap a good investment",
              "recommend a mutual fund", "good time to invest?"]:
        assert detect_advice_request(q), q
    for q in ["why was dp charge deducted", "what is the exit load on HDFC Mid Cap Fund"]:
        assert not detect_advice_request(q), q

def test_performance_requests():
    for q in ["what returns did hdfc mid cap give in 3 years", "CAGR of flexi cap", "how much will I earn in 5 years"]:
        assert detect_performance_request(q), q
    for q in ["return my money, withdrawal stuck", "expense ratio of nifty index fund"]:
        assert not detect_performance_request(q), q

def test_output_rules():
    assert find_advice("You should consider investing in HDFC Mid Cap.")
    assert find_performance("The fund delivered 24% CAGR over 5 years.")
    assert not find_performance("The Direct Plan expense ratio is 0.20% p.a. [1].")
    assert not find_performance("MTF interest is 14.95% p.a. [1].")
    assert not find_advice("An exit load of 1% applies if redeemed within 1 year [1].")

def test_sentence_split_keeps_rs_and_decimals():
    s = split_sentences("DP charges of Rs. 20 + GST apply [1]. Exit load is 1.00% within 1 year [2][3]. Last")
    assert s == ["DP charges of Rs. 20 + GST apply [1].", "Exit load is 1.00% within 1 year [2][3].", "Last"]

def test_numbers_ignore_index_names_and_markers():
    assert numbers_in("HDFC Nifty 50 Index Fund is 0.20% [1]") == {"0.2"}
    assert numbers_in("₹1,00,000 within 365 days") == {"100000", "365"}
