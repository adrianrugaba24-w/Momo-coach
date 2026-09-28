import html
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from categorizer import add_categories
from insights import generate_insights, money, spending_frame, week_windows
from momo_parser import parse_messages

INK, TEAL, GOLD, CORAL = "#10262B", "#0F7B6C", "#F2B632", "#D9573B"
CAT_COLORS = {
    "Cash withdrawal": CORAL,
    "Airtime & data": GOLD,
    "Transfers to people": "#6C8EAD",
    "Food & shopping": "#8AB17D",
    "Bills & utilities": TEAL,
    "Transport": "#14454F",
}

st.set_page_config(page_title="MoMo Coach", page_icon="💸", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=DM+Sans:wght@400;500;700&display=swap');
html, body, .stApp, [class*="st-"] { font-family: 'DM Sans', sans-serif; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: #F3F6F4 !important; color: #10262B !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background: #E4ECE8 !important; }
h1, h2, h3, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] { color: #10262B !important; }
[data-baseweb="input"], [data-baseweb="input"] input, [data-baseweb="base-input"] { background: #fff !important; color: #10262B !important; }
[data-testid="stNumberInput"] button { background: #fff !important; color: #10262B !important; }
[data-testid="stExpander"] { background: #fff; border-color: #C5D3CD; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color: #10262B !important; }
.stat b { color: #10262B; }
.note { color: #10262B; }
.block-container { max-width: 1100px; padding-top: 2.5rem; }
h1, h2, h3, .hero h1 { font-family: 'Bricolage Grotesque', sans-serif !important; letter-spacing: -0.02em; }
.hero h1 { font-size: clamp(2rem, 5vw, 3.4rem); font-weight: 800; line-height: 1.05; margin: 0 0 .5rem; color: #10262B; }
.hero .sub { font-size: 1.15rem; font-weight: 500; margin: 0 0 1.2rem; }
.privacy { color: #4C625F; font-size: .9rem; margin-bottom: 1.5rem; }
.budget { background: #E4ECE8; border-radius: 999px; height: 14px; overflow: hidden; max-width: 560px; }
.budget > div { height: 100%; border-radius: 999px; }
.budget-note { font-size: .95rem; margin: .4rem 0 0; color: #4C625F; }
.stats { display: flex; flex-wrap: wrap; margin: 2rem 0 2.2rem; border-top: 2px solid #10262B; }
.stat { flex: 1 1 200px; padding: 1rem 1.2rem 0 0; }
.stat + .stat { padding-left: 1.2rem; border-left: 1px solid #C5D3CD; }
.stat b { display: block; font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.7rem; font-weight: 800; }
.stat span { color: #4C625F; font-size: .95rem; }
.note { display: flex; gap: .8rem; padding: .85rem 1rem; margin-bottom: .6rem; background: #fff; border-left: 6px solid var(--c); border-radius: 4px 14px 14px 4px; line-height: 1.45; }
.note .ico { font-size: 1.3rem; }
</style>
""",
    unsafe_allow_html=True,
)

SAMPLE = Path(__file__).parent / "sample_data" / "sample_messages.txt"

with st.sidebar:
    st.header("Your data")
    use_sample = st.toggle("Use fake sample data", value=True)
    limit = st.number_input("Weekly spending limit (UGX, 0 = off)", min_value=0, value=0, step=10000)
    st.caption("Messages are processed in this session only. Nothing is stored or uploaded.")

if use_sample:
    raw = SAMPLE.read_text()
else:
    upload = st.file_uploader("Upload a .txt file of messages", type="txt")
    raw = st.text_area("...or paste messages (one per line)", height=200)
    if upload:
        raw = upload.read().decode("utf-8", errors="ignore")

df, failed = parse_messages(raw)
if df.empty:
    st.title("MoMo Coach")
    st.info("Paste your mobile money messages in the box above, or switch on the fake sample data in the sidebar.")
    st.stop()
df = add_categories(df)
out = spending_frame(df)
if out.empty:
    st.warning("These messages only contain money coming in. Add some spending messages to get coaching.")
    st.stop()

# ---- Hero: the coach's one-line verdict ----
this_week, prev_week = week_windows(out)
now, before = this_week["cost"].sum(), prev_week["cost"].sum()
if before > 0:
    change = (now - before) / before * 100
    sub = f"{abs(change):.0f}% {'more' if change > 0 else 'less'} than the week before ({money(before)})."
    sub_color = CORAL if change > 0 else TEAL
else:
    sub, sub_color = "Add more history to compare with earlier weeks.", TEAL

budget_html = ""
if limit > 0:
    pct = now / limit * 100
    bar = CORAL if pct > 100 else (GOLD if pct > 75 else TEAL)
    note = (f"{money(now - limit)} over your {money(limit)} weekly limit." if pct > 100
            else f"{pct:.0f}% of your {money(limit)} limit used, {money(limit - now)} left.")
    budget_html = f'<div class="budget"><div style="width:{min(pct, 100):.0f}%;background:{bar}"></div></div><p class="budget-note">{note}</p>'

st.markdown(
    f'<div class="hero"><h1>You spent {money(now)} in the last 7 days.</h1>'
    f'<p class="sub" style="color:{sub_color}">{sub}</p>{budget_html}</div>',
    unsafe_allow_html=True,
)

income = df.loc[df["direction"] == "in", "amount"].sum()
skipped = f" ({len(failed)} skipped)" if failed else ""
st.markdown(
    '<div class="stats">'
    f'<div class="stat"><b>{money(income)}</b><span>came in</span></div>'
    f'<div class="stat"><b>{money(out["amount"].sum())}</b><span>went out</span></div>'
    f'<div class="stat"><b>{money(out["fee"].sum())}</b><span>lost to fees</span></div>'
    f'<div class="stat"><b>{len(df)}</b><span>messages read{skipped}</span></div>'
    "</div>",
    unsafe_allow_html=True,
)


def tip_style(t):
    if t.startswith("Over budget"):
        return "🚨", CORAL
    if t.startswith("You've used"):
        return "🎯", GOLD
    if t.startswith("You spent"):
        return ("📈", CORAL) if " up " in t else ("📉", TEAL)
    if "cash withdrawals" in t:
        return "💡", GOLD
    if "biggest category" in t:
        return "📊", TEAL
    if "fees" in t:
        return "🧾", TEAL
    return "💰", TEAL


left, right = st.columns([3, 2], gap="large")
with left:
    st.subheader("What your coach noticed")
    for tip in generate_insights(df, limit):
        icon, color = tip_style(tip)
        st.markdown(f'<div class="note" style="--c:{color}"><span class="ico">{icon}</span><span>{html.escape(tip)}</span></div>', unsafe_allow_html=True)

with right:
    st.subheader("Where it went")
    cats = out.groupby("category")["amount"].sum().reset_index()
    chart = (
        alt.Chart(cats)
        .mark_bar(cornerRadiusEnd=6)
        .encode(
            x=alt.X("amount:Q", title=None, axis=alt.Axis(format="~s", grid=False)),
            y=alt.Y("category:N", sort="-x", title=None),
            color=alt.Color("category:N", legend=None, scale=alt.Scale(domain=list(CAT_COLORS), range=list(CAT_COLORS.values()))),
            tooltip=["category", alt.Tooltip("amount:Q", format=",.0f")],
        )
        .properties(width="container", height=260)
        .configure(background="transparent").configure_axis(labelColor=INK, domainColor="#9FB3AB", tickColor="#9FB3AB", labelFontSize=12)
        .configure_view(stroke=None)
    )
    st.altair_chart(chart, theme=None)

st.subheader("Week by week (fees included)")
weekly = out.groupby(pd.Grouper(key="datetime", freq="W-SUN"))["cost"].sum().reset_index()
weekly["week"] = "Week ending " + weekly["datetime"].dt.strftime("%d %b")
weekly["latest"] = weekly.index == weekly.index.max()
wk = (
    alt.Chart(weekly)
    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
    .encode(
        x=alt.X("week:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("cost:Q", title=None, axis=alt.Axis(format="~s", grid=True, gridColor="#D7E1DC")),
        color=alt.condition("datum.latest", alt.value(GOLD), alt.value(TEAL)),
        tooltip=["week", alt.Tooltip("cost:Q", format=",.0f")],
    )
    .properties(width="container", height=260)
    .configure(background="transparent").configure_axis(labelColor=INK, domainColor="#9FB3AB", tickColor="#9FB3AB", labelFontSize=12)
    .configure_view(stroke=None)
)
st.altair_chart(wk, theme=None)

with st.expander("See every transaction"):
    st.dataframe(df.drop(columns=["raw"]), width="stretch")
if failed:
    with st.expander(f"{len(failed)} messages could not be read"):
        st.write("Extend the patterns in momo_parser.py to handle these:")
        st.code("\n".join(failed))