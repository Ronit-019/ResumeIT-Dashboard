
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard_common import date_filter, filtered_product_data

st.set_page_config(page_title="Executive Overview", page_icon="📊", layout="wide")

st.title("Executive Overview")
st.caption("ResumeIT product performance at a glance")

start_date, end_date = date_filter()
users, events, transactions = filtered_product_data(start_date, end_date)

st.caption(f"Period: {start_date:%d %b %Y} – {end_date:%d %b %Y}")

new_users = users["user_id"].nunique()

activation_events = {
    "resume_preview_viewed",
    "ats_score_displayed",
    "ai_resume_generated",
    "cover_letter_export_succeeded",
    "mail_sent_successfully",
}
activated_users = events.loc[
    events["event_name"].isin(activation_events), "user_id"
].nunique()
activation_rate = activated_users / new_users * 100 if new_users else 0

download_attempts = events[
    events["event_name"] == "cv_download_attempted"
]
download_successes = events[
    events["event_name"] == "cv_download_succeeded"
]
downloaders = download_successes["user_id"].nunique()

successful_transactions = transactions[
    transactions["payment_status"].astype(str).str.lower() == "success"
]
paying_users = successful_transactions["user_id"].nunique()
revenue = pd.to_numeric(
    successful_transactions["recognized_revenue_inr"], errors="coerce"
).fillna(0).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("New Users", f"{new_users:,}")
c2.metric("Activation Rate", f"{activation_rate:.1f}%")
c3.metric("Unique CV Downloaders", f"{downloaders:,}")
c4.metric("Recognized Revenue", f"₹{revenue:,.0f}")

st.divider()
st.subheader("Acquisition Trend")

if users.empty:
    st.info("No new users in this date range.")
else:
    daily = users.assign(
        date=users["first_open_at"].dt.tz_convert("Asia/Kolkata").dt.date
    ).groupby("date")["user_id"].nunique().reset_index(name="New Users")

    fig = px.line(
        daily, x="date", y="New Users", markers=True,
        labels={"date": "Date"},
    )
    st.plotly_chart(fig, use_container_width=True)

