from pathlib import Path

import pandas as pd
import streamlit as st

from categorizer import add_categories
from insights import generate_insights, money, spending_frame
from momo_parser import parse_messages

st.set_page_config(page_title="MoMo Coach", page_icon="💸", layout="wide")
st.title("💸 Mobile Money Spending Coach")
st.caption("Your messages are processed in this session only. Nothing is stored or uploaded anywhere.")

SAMPLE = Path(__file__).parent / "sample_data" / "sample_messages.txt"

with st.sidebar:
    st.header("Your data")
    use_sample = st.toggle("Use fake sample data", value=True)
    limit = st.number_input("Weekly spending limit (UGX, 0 = off)", min_value=0, value=0, step=10000)

if use_sample:
    raw = SAMPLE.read_text()
else:
    upload = st.file_uploader("Upload a .txt file of messages", type="txt")
    raw = st.text_area("...or paste messages (one per line)", height=200)
    if upload:
        raw = upload.read().decode("utf-8", errors="ignore")

df, failed = parse_messages(raw)
if df.empty:
    st.info("Paste some messages or switch on the sample data to begin.")
    st.stop()
df = add_categories(df)
out = spending_frame(df)

income = df.loc[df["direction"] == "in", "amount"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Money in", money(income))
c2.metric("Money out", money(out["amount"].sum()))
c3.metric("Fees paid", money(out["fee"].sum()))
c4.metric("Messages read", f"{len(df)}" + (f" ({len(failed)} skipped)" if failed else ""))

st.subheader("🧠 Your coach says")
for tip in generate_insights(df, limit):
    st.info(tip)

left, right = st.columns(2)
with left:
    st.subheader("Spending by category")
    st.bar_chart(out.groupby("category")["amount"].sum().sort_values(ascending=False))
with right:
    st.subheader("Weekly spending (incl. fees)")
    st.line_chart(out.groupby(pd.Grouper(key="datetime", freq="W-SUN"))["cost"].sum())

with st.expander("See parsed transactions"):
    st.dataframe(df.drop(columns=["raw"]), use_container_width=True)
if failed:
    with st.expander(f"{len(failed)} messages could not be parsed"):
        st.write("Extend the patterns in momo_parser.py to handle these:")
        st.code("\n".join(failed))
