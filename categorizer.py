"""Rule-based categories: easy to read, easy to explain, easy to extend."""

KEYWORDS = {
    "Bills & utilities": ["umeme", "nwsc", "yaka", "dstv", "gotv", "startimes", "water", "electric", "rent"],
    "Transport": ["safeboda", "uber", "bolt", "faras", "fuel", "petrol", "taxi"],
    "Food & shopping": ["kfc", "cafe", "restaurant", "supermarket", "shoprite", "carrefour", "java", "pizza", "market"],
}


def categorize(row):
    if row["type"] == "received":
        return "Income"
    if row["type"] == "withdrawal":
        return "Cash withdrawal"
    if row["type"] == "airtime":
        return "Airtime & data"
    who = row["counterparty"].lower()
    for category, words in KEYWORDS.items():
        if any(w in who for w in words):
            return category
    return "Transfers to people"


def add_categories(df):
    df = df.copy()
    df["category"] = df.apply(categorize, axis=1)
    return df
