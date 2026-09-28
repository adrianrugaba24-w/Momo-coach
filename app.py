import html
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from categorizer import add_categories
from insights import generate_insights, money, spending_frame, week_windows
from momo_parser import parse_messages

# ---------- Theme ----------
INK, MUTED, BG = "#10262B", "#647773", "#F5F7F6"
TEAL, GOLD, CORAL, BLUE = "#087F6A", "#E6A817", "#D9573B", "#4E7896"
BORDER, CARD = "#D7E1DC", "#FFFFFF"
CAT_COLORS = {
    "Cash withdrawal": CORAL, "Airtime & data": GOLD,
    "Transfers to people": BLUE, "Food & shopping": "#78A66A",
    "Bills & utilities": TEAL, "Transport": "#245A63",
}

st.set_page_config(page_title="MoMo Coach", page_icon="💸", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=DM+Sans:wght@400;500;600;700&display=swap');
.stApp,[data-testid="stAppViewContainer"]{{background:{BG};color:{INK}}}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div{{background:#E7EFEB!important}}
.stApp p,.stApp label,.stApp li,.stApp input,.stApp textarea,.stApp button{{font-family:'DM Sans',sans-serif}}
h1,h2,h3{{font-family:'Bricolage Grotesque',sans-serif!important;color:{INK}!important;letter-spacing:-.025em}}
.block-container{{max-width:1250px;padding-top:2rem;padding-bottom:4rem}}
.hero{{display:flex;justify-content:space-between;align-items:end;gap:2rem;padding:1rem 0 1.6rem;border-bottom:1px solid {BORDER}}}
.eyebrow{{color:{TEAL};font-size:.76rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.5rem}}
.hero h1{{font-size:clamp(2.1rem,4vw,3.7rem);line-height:1.02;margin:0}}
.hero p{{color:{MUTED};font-size:1rem;max-width:720px;margin:.65rem 0 0}}
.badge{{background:{INK};color:white;padding:.6rem .85rem;border-radius:999px;font-size:.8rem;font-weight:700;white-space:nowrap}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:1.3rem 0}}
.kpi{{background:{CARD};border:1px solid {BORDER};border-radius:16px;padding:1rem 1.1rem;box-shadow:0 4px 18px rgba(16,38,43,.04)}}
.kpi .line{{height:4px;width:38px;border-radius:99px;margin-bottom:.8rem}}
.kpi .label{{color:{MUTED};font-size:.76rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}}
.kpi .value{{font-family:'Bricolage Grotesque';font-size:1.7rem;font-weight:800;margin:.25rem 0}}
.kpi .foot{{color:{MUTED};font-size:.77rem}}
.section{{margin:1.7rem 0 .7rem}}
.section h2{{font-size:1.35rem;margin:0}}
.section p{{color:{MUTED};font-size:.88rem;margin:.2rem 0 0}}
.panel{{background:{CARD};border:1px solid {BORDER};border-radius:16px;padding:1rem 1.15rem}}
.budget{{background:{INK};color:white;border-radius:16px;padding:1.1rem 1.2rem;margin-bottom:1.3rem}}
.budget *{{color:white}}
.budget-top{{display:flex;justify-content:space-between;align-items:center}}
.progress{{height:10px;background:rgba(255,255,255,.18);border-radius:99px;overflow:hidden;margin:.8rem 0 .45rem}}
.progress>div{{height:100%;border-radius:99px}}
.insight{{display:flex;gap:.75rem;padding:.8rem .9rem;background:#F7FAF8;border-left:4px solid {TEAL};border-radius:10px;margin-bottom:.6rem;line-height:1.4}}
.insight-text{{font-size:.9rem}}
.spotlight{{background:{CARD};border:1px solid {BORDER};border-radius:16px;padding:1.15rem}}
.spotlight .big{{font-family:'Bricolage Grotesque';font-size:2rem;font-weight:800}}
.minirow{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:1rem}}
.mini{{background:#EAF0ED;border-radius:10px;padding:.7rem}}
.mini small{{color:{MUTED}}}.mini b{{display:block;margin-top:.2rem}}
.txwrap{{max-height:470px;overflow:auto;background:white;border:1px solid {BORDER};border-radius:12px}}
table.tx{{width:100%;border-collapse:collapse;font-size:.84rem;color:{INK}}}
table.tx th{{position:sticky;top:0;background:#E7EFEB;text-align:left;padding:.65rem .75rem;z-index:2}}
table.tx td{{padding:.55rem .75rem;border-top:1px solid #EDF2EF;white-space:nowrap}}
@media(max-width:850px){{.hero{{align-items:flex-start;flex-direction:column}}.kpis{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:520px){{.kpis{{grid-template-columns:1fr}}.minirow{{grid-template-columns:1fr}}}}
</style>
""", unsafe_allow_html=True)

SAMPLE = Path(__file__).parent / "sample_data" / "sample_messages.txt"

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 💸 MoMo Coach")
    st.caption("Turn MoMo SMS history into a simple financial picture.")
    st.divider()
    use_sample = st.toggle("Use fake sample data", True)
    limit = st.number_input("Weekly spending limit (UGX)", 0, value=0, step=10000)
    st.divider()
    st.markdown("**Privacy**")
    st.caption("Messages are processed in this session only. Nothing is stored or uploaded.")
    if not use_sample:
        upload = st.file_uploader("Upload .txt messages", type="txt")
        pasted = st.text_area("Or paste messages", height=160, placeholder="One message per line…")
    else:
        upload, pasted = None, ""

raw = SAMPLE.read_text(encoding="utf-8") if use_sample else pasted
if upload:
    raw = upload.read().decode("utf-8", errors="ignore")

df, failed = parse_messages(raw)
if df.empty:
    st.markdown("""<div class="hero"><div><div class="eyebrow">Private financial dashboard</div><h1>Your money, made clearer.</h1><p>Upload your mobile-money messages to see spending patterns, trends and coaching.</p></div></div>""", unsafe_allow_html=True)
    st.info("Add MoMo messages from the sidebar to begin.")
    st.stop()

df = add_categories(df)
out = spending_frame(df)
if out.empty:
    st.warning("No outgoing transactions were found in these messages.")
    st.stop()

# ---------- Metrics ----------
this_week, prev_week = week_windows(out)
now = float(this_week["cost"].sum())
before = float(prev_week["cost"].sum())
change = ((now - before) / before * 100) if before else None
income = float(df.loc[df["direction"] == "in", "amount"].sum())
total_out = float(out["amount"].sum())
fees = float(out["fee"].sum())

cats = out.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
cats["share"] = cats["amount"] / cats["amount"].sum() * 100
largest = cats.iloc[0]

change_text = "No previous week available"
if change is not None:
    change_text = f"{abs(change):.0f}% {'higher' if change > 0 else 'lower'} than last week"

st.markdown(f"""
<div class="hero">
  <div><div class="eyebrow">Financial snapshot</div>
  <h1>You spent {money(now)} this week.</h1>
  <p>{html.escape(change_text)}. Your MoMo activity is summarized into trends, categories and practical observations.</p></div>
  <div class="badge">🔒 Session only</div>
</div>
""", unsafe_allow_html=True)

change_color = CORAL if (change or 0) > 0 else TEAL
st.markdown(f"""
<div class="kpis">
 <div class="kpi"><div class="line" style="background:{TEAL}"></div><div class="label">7-day spending</div><div class="value">{money(now)}</div><div class="foot" style="color:{change_color}">{change_text}</div></div>
 <div class="kpi"><div class="line" style="background:{BLUE}"></div><div class="label">Money in</div><div class="value">{money(income)}</div><div class="foot">Across {len(df)} messages</div></div>
 <div class="kpi"><div class="line" style="background:{GOLD}"></div><div class="label">Fees paid</div><div class="value">{money(fees)}</div><div class="foot">Included in weekly cost</div></div>
 <div class="kpi"><div class="line" style="background:{CORAL}"></div><div class="label">Money out</div><div class="value">{money(total_out)}</div><div class="foot">{len(out)} outgoing transactions</div></div>
</div>
""", unsafe_allow_html=True)

if limit > 0:
    pct = now / limit * 100
    color = CORAL if pct > 100 else GOLD if pct > 75 else TEAL
    remaining = limit - now
    message = f"{money(abs(remaining))} {'over' if remaining < 0 else 'remaining'}"
    st.markdown(f"""
    <div class="budget"><div class="budget-top"><div><small>WEEKLY BUDGET</small><div style="font-size:1.3rem;font-weight:800">{money(now)} / {money(limit)}</div></div><b>{min(pct,100):.0f}%</b></div>
    <div class="progress"><div style="width:{min(pct,100):.0f}%;background:{color}"></div></div><small>{message} on your limit.</small></div>
    """, unsafe_allow_html=True)

# ---------- Charts ----------
left, right = st.columns([1.5, 1], gap="large")
with left:
    st.markdown('<div class="section"><h2>Spending trend</h2><p>Weekly cost, including fees.</p></div>', unsafe_allow_html=True)
    weekly = out.groupby(pd.Grouper(key="datetime", freq="W-SUN"))["cost"].sum().reset_index()
    weekly["week"] = "Week ending " + weekly["datetime"].dt.strftime("%d %b")
    weekly["latest"] = weekly.index == weekly.index.max()
    chart = alt.Chart(weekly).mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7).encode(
        x=alt.X("week:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("cost:Q", title=None, axis=alt.Axis(format="~s", grid=True, gridColor="#E0E8E4")),
        color=alt.condition("datum.latest", alt.value(GOLD), alt.value(TEAL)),
        tooltip=["week", alt.Tooltip("cost:Q", title="Cost", format=",.0f")]
    ).properties(height=300).configure(background="transparent").configure_axis(labelColor=INK, domainColor=BORDER, tickColor=BORDER).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

with right:
    st.markdown('<div class="section"><h2>Where it went</h2><p>Categories ranked by spending.</p></div>', unsafe_allow_html=True)
    chart2 = alt.Chart(cats).mark_bar(cornerRadiusEnd=6).encode(
        x=alt.X("amount:Q", title=None, axis=alt.Axis(format="~s", grid=False)),
        y=alt.Y("category:N", sort="-x", title=None),
        color=alt.Color("category:N", legend=None, scale=alt.Scale(domain=list(CAT_COLORS), range=list(CAT_COLORS.values()))),
        tooltip=["category", alt.Tooltip("amount:Q", title="Spent", format=",.0f"), alt.Tooltip("share:Q", title="Share", format=".1f")]
    ).properties(height=300).configure(background="transparent").configure_axis(labelColor=INK, domainColor=BORDER, tickColor=BORDER).configure_view(stroke=None)
    st.altair_chart(chart2, use_container_width=True)

# ---------- Coach ----------
st.markdown('<div class="section"><h2>What your coach noticed</h2><p>Patterns detected from your transactions.</p></div>', unsafe_allow_html=True)
coach_left, coach_right = st.columns([1.2, .8], gap="large")
with coach_left:
    for tip in generate_insights(df, limit):
        icon, color = "💰", TEAL
        if tip.startswith("Over budget"): icon, color = "🚨", CORAL
        elif tip.startswith("You've used"): icon, color = "🎯", GOLD
        elif tip.startswith("You spent"): icon, color = (("📈", CORAL) if " up " in tip else ("📉", TEAL))
        elif "cash withdrawals" in tip: icon, color = "💡", GOLD
        elif "biggest category" in tip: icon, color = "📊", TEAL
        elif "fees" in tip: icon, color = "🧾", BLUE
        st.markdown(f'<div class="insight" style="border-left-color:{color}"><span>{icon}</span><span class="insight-text">{html.escape(tip)}</span></div>', unsafe_allow_html=True)
with coach_right:
    st.markdown(f"""
    <div class="spotlight"><div class="eyebrow">Category spotlight</div>
    <h3 style="margin:.1rem 0 .4rem">{html.escape(str(largest['category']))}</h3>
    <div class="big">{money(largest['amount'])}</div>
    <p style="color:{MUTED}">{largest['share']:.1f}% of spending this period.</p>
    <div class="minirow"><div class="mini"><small>Total spent</small><b>{money(total_out)}</b></div><div class="mini"><small>Transactions</small><b>{len(out)}</b></div><div class="mini"><small>Average</small><b>{money(total_out/max(len(out),1))}</b></div></div></div>
    """, unsafe_allow_html=True)

# ---------- Transactions ----------
st.markdown('<div class="section"><h2>Transactions</h2><p>Filter the raw transaction history without leaving the dashboard.</p></div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1.3, 1, 1])
with c1: search = st.text_input("Search", placeholder="Category, amount, message…")
with c2: selected_cat = st.selectbox("Category", ["All"] + sorted(out["category"].dropna().unique().tolist()))
with c3: selected_type = st.selectbox("Type", ["All", "in", "out"])

tx = df.drop(columns=["raw"], errors="ignore").copy()
if selected_cat != "All": tx = tx[tx["category"] == selected_cat]
if selected_type != "All": tx = tx[tx["direction"] == selected_type]
if search:
    tx = tx[tx.astype(str).apply(lambda c: c.str.contains(search, case=False, na=False)).any(axis=1)]
if "datetime" in tx: tx["datetime"] = pd.to_datetime(tx["datetime"]).dt.strftime("%d %b %Y %H:%M")
for col in ["amount", "fee", "balance"]:
    if col in tx: tx[col] = tx[col].map(lambda v: "" if pd.isna(v) else f"{v:,.0f}")
st.caption(f"Showing {len(tx)} transaction(s)")
st.markdown(f'<div class="txwrap">{tx.to_html(index=False, classes="tx", border=0)}</div>', unsafe_allow_html=True)

if failed:
    with st.expander(f"{len(failed)} messages could not be read"):
        st.write("Extend the patterns in momo_parser.py to handle these:")
        st.code("\n".join(failed))
