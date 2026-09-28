"""The 'coach': plain rule-based tips computed from the parsed data."""
import pandas as pd


def money(x):
    return f"UGX {x:,.0f}"


def spending_frame(df):
    """Money that left the wallet, with fees folded into a `cost` column."""
    out = df[df["direction"] == "out"].copy()
    out["cost"] = out["amount"] + out["fee"]
    return out


def week_windows(out):
    """(this_week, previous_week) = last 7 days of data vs the 7 days before."""
    end = out["datetime"].max().normalize()
    this_start = end - pd.Timedelta(days=6)
    prev_start = end - pd.Timedelta(days=13)
    this_week = out[out["datetime"] >= this_start]
    prev_week = out[(out["datetime"] >= prev_start) & (out["datetime"] < this_start)]
    return this_week, prev_week


def generate_insights(df, weekly_limit=0):
    out = spending_frame(df)
    if out.empty:
        return ["No spending found yet. Add some messages to get coaching."]
    tips = []
    this_week, prev_week = week_windows(out)
    now, before = this_week["cost"].sum(), prev_week["cost"].sum()

    # 1. Week over week
    if before > 0:
        change = (now - before) / before * 100
        direction = "up" if change > 0 else "down"
        tips.append(f"You spent {money(now)} in the last 7 days, {direction} {abs(change):.0f}% from {money(before)} the week before.")
    else:
        tips.append(f"You spent {money(now)} in the last 7 days.")

    # 2. Budget goal
    if weekly_limit > 0:
        pct = now / weekly_limit * 100
        if pct > 100:
            tips.append(f"Over budget: you're {money(now - weekly_limit)} past your {money(weekly_limit)} weekly limit.")
        else:
            tips.append(f"You've used {pct:.0f}% of your {money(weekly_limit)} weekly limit ({money(weekly_limit - now)} left).")

    # 3. Biggest category
    by_cat = out.groupby("category")["amount"].sum().sort_values(ascending=False)
    top, share = by_cat.index[0], by_cat.iloc[0] / out["amount"].sum() * 100
    tips.append(f"Your biggest category is {top} at {share:.0f}% of spending ({money(by_cat.iloc[0])}).")

    # 4. Fees, and whether grouping withdrawals would help
    fees = out["fee"].sum()
    tips.append(f"You paid {money(fees)} in fees in total.")
    w = out[out["type"] == "withdrawal"]
    if len(w) >= 3:
        saving = w["fee"].sum() / 2
        tips.append(f"You made {len(w)} cash withdrawals costing {money(w['fee'].sum())} in fees. Withdrawing half as often, in bigger amounts, could save about {money(saving)} (check your network's fee bands first).")

    # 5. Largest single expense
    big = out.loc[out["amount"].idxmax()]
    label = big["counterparty"] or big["type"]
    tips.append(f"Your largest single expense was {money(big['amount'])} to {label} on {big['datetime']:%d %b}.")
    return tips
