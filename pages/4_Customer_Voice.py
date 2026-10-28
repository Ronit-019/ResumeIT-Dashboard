
import pandas as pd
import plotly.express as px
import streamlit as st
from google_play_scraper import app
from dashboard_common import load_data, filter_dates, review_date_filter

st.set_page_config(
    page_title="Customer Voice & Retention",
    page_icon="💬",
    layout="wide",
)

st.title("Customer Voice & Retention")
st.caption("Explore actual collected text reviews and synthetic repeat usage.")

# Independent date filter for reviews
start_date, end_date = review_date_filter()
_, events, _, reviews = load_data()

filtered_reviews = filter_dates(
    reviews, "review_date", start_date, end_date
)

st.caption(
    f"Review period: {start_date:%d %b %Y} – {end_date:%d %b %Y}"
)

st.subheader("Overall Google Play Store Ratings")
st.caption(
    "Overall Play Store star-rating distribution. "
    "These ratings are separate from the collected text reviews below."
)

try:
    result = app(
        "com.pixsterstudio.resumebuilder",
        lang="en",
        country="us",
    )
    histogram = result["histogram"]
    total_ratings = result["ratings"]

    rating_data = pd.DataFrame({
        "Star Rating": [1, 2, 3, 4, 5],
        "Ratings": histogram,
    })

    st.metric("Total Star Ratings", f"{total_ratings:,}")

    fig = px.bar(
        rating_data,
        x="Star Rating",
        y="Ratings",
        title="All Star Ratings (1–5 Stars)",
        text_auto=True,
    )
    st.plotly_chart(fig, use_container_width=True)

except Exception as exc:
    st.warning(
        "Could not fetch the live Play Store rating histogram. "
        "Check your internet connection and try again."
    )

st.subheader("Customer Voice")
st.caption(
    "These are actual collected text reviews, not the full Play Store "
    "rating histogram."
)

if filtered_reviews.empty:
    st.info("No reviews were found in the selected review date range.")
else:
    scores = pd.to_numeric(filtered_reviews["score"], errors="coerce")
    average_rating = scores.mean()
    review_count = len(filtered_reviews)

    sentiments = filtered_reviews["sentiment"].fillna("Unknown")
    positive = int((sentiments == "Positive").sum())
    neutral = int((sentiments == "Neutral").sum())
    negative = int((sentiments == "Negative").sum())

    a, b, c, d = st.columns(4)
    a.metric("Text Reviews", f"{review_count:,}")
    b.metric(
        "Average Rating",
        f"{average_rating:.2f}/5" if pd.notna(average_rating) else "N/A",
    )
    c.metric("Positive Reviews", f"{positive:,}")
    d.metric("Negative Reviews", f"{negative:,}")

    left, right = st.columns(2)

    with left:
        rating_counts = (
            scores.dropna()
            .value_counts()
            .reindex([1, 2, 3, 4, 5], fill_value=0)
            .rename_axis("Rating")
            .reset_index(name="Reviews")
        )
        fig = px.bar(
            rating_counts, x="Rating", y="Reviews",
            title="Star Rating Distribution", text_auto=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        sentiment_counts = (
            sentiments.value_counts()
            .rename_axis("Sentiment")
            .reset_index(name="Reviews")
        )
        fig = px.pie(
            sentiment_counts, names="Sentiment", values="Reviews",
            hole=0.45, title="Review Sentiment",
        )
        st.plotly_chart(fig, use_container_width=True)

    

    st.subheader("Text Review Ratings by App Version")

    version_reviews = filtered_reviews.dropna(
        subset=["appVersion", "score"]
    ).copy()
    version_reviews["score"] = pd.to_numeric(
        version_reviews["score"], errors="coerce"
    )
    version_reviews = version_reviews[
        version_reviews["score"].isin([1, 2, 3, 4, 5])
    ]

    versions = sorted(version_reviews["appVersion"].unique(), reverse=True)

    selected_version = st.selectbox(
        "Filter by app version",
        ["All versions"] + versions,
        key="text_review_version",
    )

    if selected_version != "All versions":
        version_reviews = version_reviews[
            version_reviews["appVersion"] == selected_version
        ]

    if version_reviews.empty:
        st.info("No rated text reviews available for this version.")
    else:
        version_counts = (
            version_reviews["score"]
            .value_counts()
            .reindex([1, 2, 3, 4, 5], fill_value=0)
            .rename_axis("Star Rating")
            .reset_index(name="Text Reviews")
        )

        fig = px.bar(
            version_counts,
            x="Star Rating",
            y="Text Reviews",
            title=(
                f"Text Review Ratings — {selected_version}"
                if selected_version != "All versions"
                else "Text Review Ratings — All Versions"
            ),
            text_auto=True,
        )
        st.plotly_chart(fig, use_container_width=True)


    st.subheader("Review Explorer")
    sentiment_filter = st.selectbox(
        "Filter by sentiment",
        ["All", "Positive", "Neutral", "Negative"],
    )

    displayed = filtered_reviews.copy()
    if sentiment_filter != "All":
        displayed = displayed[displayed["sentiment"] == sentiment_filter]

    columns = [
        column for column in ["review_date", "score", "sentiment", "content"]
        if column in displayed.columns
    ]
    st.dataframe(
        displayed[columns].sort_values("review_date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

# Exploratory repeat usage using the product analytics date range separately
st.divider()
st.subheader("Meaningful Repeat Usage")
st.caption(
    "Exploratory metric from synthetic product events. "
    "It is not standard D1/D7/D30 retention."
)

product_start, product_end = None, None
product_dates = st.date_input(
    "Product activity dates for repeat usage",
    value=(
        pd.Timestamp("2026-05-02").date(),
        pd.Timestamp("2026-10-27").date(),
    ),
    key="retention_product_dates",
)

if isinstance(product_dates, (tuple, list)) and len(product_dates) == 2:
    product_start, product_end = product_dates
    product_events = filter_dates(
        events, "timestamp", product_start, product_end
    )

    meaningful_names = {
        "resume_preview_viewed",
        "ats_score_displayed",
        "ai_resume_generated",
        "cover_letter_export_succeeded",
        "mail_sent_successfully",
    }

    meaningful = product_events[
        product_events["event_name"].isin(meaningful_names)
    ].copy()

    if not meaningful.empty:
        meaningful["activity_date"] = (
            meaningful["timestamp"]
            .dt.tz_convert("Asia/Kolkata")
            .dt.date
        )

        active_days = meaningful.groupby("user_id")[
            "activity_date"
        ].nunique()

        active_users = int(meaningful["user_id"].nunique())
        repeat_users = int((active_days >= 3).sum())
        repeat_rate = repeat_users / active_users * 100 if active_users else 0

        a, b, c = st.columns(3)
        a.metric("Meaningfully Active Users", f"{active_users:,}")
        b.metric("Repeat Users (3+ days)", f"{repeat_users:,}")
        c.metric("Repeat Usage Rate", f"{repeat_rate:.1f}%")
    else:
        st.info("No meaningful product activity in that period.")

