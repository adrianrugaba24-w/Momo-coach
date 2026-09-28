"""Turn raw mobile money SMS text into a structured table.

Supports messages that look like the samples in sample_data/. Real MTN MoMo /
Airtel Money wording differs slightly, so extend the patterns below to match
your own (anonymised!) messages.
"""
import re
import pandas as pd

AMOUNT = re.compile(r"UGX\s*([\d,]+(?:\.\d+)?)", re.I)
FEE = re.compile(r"\bfee:?\s*UGX\s*([\d,]+(?:\.\d+)?)", re.I)
BALANCE = re.compile(r"\bbal(?:ance)?:?\s*UGX\s*([\d,]+(?:\.\d+)?)", re.I)
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DMY_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
TIME = re.compile(r"\b(\d{2}:\d{2}(?::\d{2})?)\b")
# "to JOHN DOE 0772..." / "from agent MARY 445566 on ..." -> the name in between
COUNTERPARTY = re.compile(
    r"\b(?:to|from)\s+(?:agent\s+)?(.+?)(?=\s+(?:\d{6,}|on|for|fee|bal|balance|tid)\b|[.,]|$)",
    re.I,
)

# Order matters: the first pattern that matches decides the message type.
TYPE_RULES = [
    ("received", re.compile(r"\breceived\b", re.I)),
    ("withdrawal", re.compile(r"\bwithdr[ae]w", re.I)),
    ("airtime", re.compile(r"\b(airtime|data bundle|bundle)\b", re.I)),
    ("payment", re.compile(r"\b(payment of|paid)\b", re.I)),
    ("sent", re.compile(r"\b(sent|transferred)\b", re.I)),
]


def _num(text):
    return float(text.replace(",", ""))


def _find_datetime(text):
    m = ISO_DATE.search(text)
    if m:
        y, mo, d = m.groups()
    else:
        m = DMY_DATE.search(text)
        if not m:
            return None
        d, mo, y = m.groups()
    t = TIME.search(text)
    return pd.Timestamp(f"{y}-{mo}-{d} {t.group(1) if t else '00:00'}")


def parse_message(text):
    """Parse one SMS. Returns a dict, or None if we can't understand it."""
    text = " ".join(text.split())
    if not text:
        return None
    kind = next((k for k, pat in TYPE_RULES if pat.search(text)), None)
    amount = AMOUNT.search(text)
    when = _find_datetime(text)
    if not (kind and amount and when is not None):
        return None

    fee = FEE.search(text)
    bal = BALANCE.search(text)
    who = COUNTERPARTY.search(text)
    return {
        "datetime": when,
        "type": kind,
        "amount": _num(amount.group(1)),
        "fee": _num(fee.group(1)) if fee else 0.0,
        "balance": _num(bal.group(1)) if bal else None,
        "counterparty": who.group(1).strip() if who else "",
        "direction": "in" if kind == "received" else "out",
        "raw": text,
    }


def parse_messages(raw):
    """Parse many messages (one per line, or separated by blank lines).

    Returns (DataFrame of parsed rows, list of lines we couldn't parse).
    """
    raw = raw.strip()
    chunks = re.split(r"\n\s*\n", raw) if re.search(r"\n\s*\n", raw) else raw.splitlines()
    rows, failed = [], []
    for chunk in chunks:
        if not chunk.strip():
            continue
        row = parse_message(chunk)
        (rows if row else failed).append(row or chunk.strip())
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("datetime").reset_index(drop=True)
    return df, failed
