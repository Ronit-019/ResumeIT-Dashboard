
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_common import date_filter, filtered_product_data, load_data

st.set_page_config(
    page_title="Monetization & Reliability",
    page_icon="💰",
    layout="wide",
)

st.title("Monetization & Reliability")

start_date, end_date = date_filter()
_, events, transactions = filtered_product_data(start_date, end_date)

st.caption(f"Period: {start_date:%d %b %Y} – {end_date:%d %b %Y}")

# Successful transactions in the selected transaction-date period
successful = transactions[
    transactions["payment_status"].astype(str).str.lower().eq("success")
].copy()

successful["recognized_revenue_inr"] = pd.to_numeric(
    successful["recognized_revenue_inr"], errors="coerce"
).fillna(0)

revenue = successful["recognized_revenue_inr"].sum()
purchases = len(successful)
payers = successful["user_id"].nunique()
arppu = revenue / payers if payers else 0

# Paywall conversion: selected-period viewers who purchase within 7 days
# of a view. Purchase events are checked across the full transaction history.
_, all_events, all_transactions, _ = load_data()

paywalls = events.loc[
    events["event_name"] == "paywall_viewed",
    ["user_id", "timestamp"],
].drop_duplicates()

all_successful = all_transactions[
    all_transactions["payment_status"].astype(str).str.lower().eq("success")
].copy()

all_successful["transaction_at"] = pd.to_datetime(
    all_successful["transaction_at"], utc=True, errors="coerce"
)

converted = set()
for user_id, views in paywalls.groupby("user_id"):
    purchases_for_user = all_successful[
        all_successful["user_id"] == user_id
    ]["transaction_at"]

    for viewed_at in views["timestamp"]:
        if (
            (purchases_for_user >= viewed_at)
            & (purchases_for_user <= viewed_at + pd.Timedelta(days=7))
        ).any():
            converted.add(user_id)
            break

viewers = paywalls["user_id"].nunique()
paywall_conversion = len(converted) / viewers * 100 if viewers else 0

st.subheader("Monetization")
a, b, c, d = st.columns(4)
a.metric("Recognized Revenue", f"₹{revenue:,.0f}")
b.metric("Successful Purchases", f"{purchases:,}")
c.metric("Unique Paying Users", f"{payers:,}")
d.metric("ARPPU", f"₹{arppu:,.2f}")

e, f = st.columns(2)
e.metric("Paywall Conversion (estimated)", f"{paywall_conversion:.1f}%")
f.metric(
    "Paywall Abandonment (estimated)",
    f"{100 - paywall_conversion:.1f}%" if viewers else "N/A",
)

if not successful.empty:
    by_plan = (
        successful.groupby("plan", dropna=False)
        .agg(
            Purchases=("transaction_id", "count"),
            Revenue=("recognized_revenue_inr", "sum"),
            Payers=("user_id", "nunique"),
        )
        .reset_index()
    )

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            by_plan, x="plan", y="Revenue", text_auto=".2s",
            title="Recognized Revenue by Plan",
            labels={"plan": "Plan", "Revenue": "Revenue (₹)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.bar(
            by_plan, x="plan", y="Purchases", text_auto=True,
            title="Successful Purchases by Plan",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(by_plan, use_container_width=True, hide_index=True)
else:
    st.info("No successful purchases in this period.")

st.divider()
st.subheader("Reliability")

upload_attempts = events[
    events["event_name"] == "resume_upload_attempted"
]
parse_successes = events[
    events["event_name"] == "resume_parse_succeeded"
]

# Use event counts consistently for attempt-based rates.
upload_count = len(upload_attempts)
parse_count = len(parse_successes)
parse_rate = parse_count / upload_count * 100 if upload_count else 0

download_attempts = events[
    events["event_name"] == "cv_download_attempted"
]
download_successes = events[
    events["event_name"] == "cv_download_succeeded"
]
download_rate = (
    len(download_successes) / len(download_attempts) * 100
    if len(download_attempts) else 0
)

a, b, c, d = st.columns(4)
a.metric("Upload Attempts", f"{upload_count:,}")
b.metric("Parse Successes", f"{parse_count:,}")
c.metric("Parsing Success Rate", f"{parse_rate:.1f}%")
d.metric("CV Download Success Rate", f"{download_rate:.1f}%")

st.caption(
    "Product analytics data is synthetic. Revenue uses successful "
    "transactions within the selected period. Paywall conversion is an "
    "estimate based on a seven-day post-view attribution window; it does "
    "not establish that a specific paywall caused a purchase."
)
