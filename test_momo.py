import pandas as pd
from categorizer import add_categories, categorize
from insights import generate_insights
from momo_parser import parse_message, parse_messages

SENT = "You have sent UGX 20,000 to JOHN DOE 0772000002 on 2026-09-10 20:11:11. Fee UGX 500. Balance UGX 103,070."
WITHDRAW = "You have withdrawn UGX 40,000 from agent MARY AGENT 445566 on 2026-09-09 12:05:00. Fee UGX 1,100. Balance UGX 123,570."


def test_sent():
    r = parse_message(SENT)
    assert (r["type"], r["amount"], r["fee"], r["balance"]) == ("sent", 20000, 500, 103070)
    assert r["counterparty"] == "JOHN DOE"
    assert r["direction"] == "out"
    assert r["datetime"] == pd.Timestamp("2026-09-10 20:11:11")


def test_withdrawal_counterparty():
    r = parse_message(WITHDRAW)
    assert r["type"] == "withdrawal" and r["counterparty"] == "MARY AGENT"


def test_received_is_income():
    r = parse_message("You have received UGX 50,000 from JANE SMITH 0701000009 on 2026-09-12 10:00:00. Balance UGX 80,000.")
    assert r["direction"] == "in"
    assert categorize(r) == "Income"


def test_garbage_returns_none():
    assert parse_message("Dear customer, enjoy 20% off this weekend!") is None
    assert parse_message("") is None


def test_categories():
    assert categorize(parse_message("Payment of UGX 25,000 to UMEME for meter 1 successful on 2026-09-07 18:30:05. Fee UGX 0.")) == "Bills & utilities"
    assert categorize(parse_message(SENT)) == "Transfers to people"


def test_sample_file_parses_fully():
    raw = open("sample_data/sample_messages.txt").read()
    df, failed = parse_messages(raw)
    assert failed == [] and len(df) == 29
    assert generate_insights(add_categories(df), weekly_limit=200000)
