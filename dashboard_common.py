
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
IST = "Asia/Kolkata"


@st.cache_data
def load_data():
    users = pd.read_csv(DATA_DIR / "users.csv")
    events = pd.read_csv(DATA_DIR / "events.csv")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    reviews = pd.read_csv(DATA_DIR / "app_reviews_with_sentiment.csv")

    for df, column in [
        (users, "first_open_at"),
        (events, "timestamp"),
        (transactions, "transaction_at"),
    ]:
        df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")

    # Convert review timestamps to UTC.
    reviews["review_date"] = pd.to_datetime(
        reviews["at"],
        utc=True,
        errors="coerce",
    )

    return users, events, transactions, reviews


def filter_dates(df, column, start_date, end_date):
    timestamps = pd.to_datetime(df[column], utc=True, errors="coerce")
    start = pd.Timestamp(start_date, tz=IST).tz_convert("UTC")
    end = (
        pd.Timestamp(end_date, tz=IST) + pd.Timedelta(days=1)
    ).tz_convert("UTC")

    return df.loc[
        timestamps.notna() & (timestamps >= start) & (timestamps < end)
    ].copy()


def date_filter(key="product"):
    users, events, transactions, _ = load_data()

    timestamps = pd.concat([
        users["first_open_at"],
        events["timestamp"],
        transactions["transaction_at"],
    ]).dropna()

    min_date = timestamps.min().tz_convert(IST).date()
    max_date = timestamps.max().tz_convert(IST).date()
    today = pd.Timestamp.now(tz=IST).date()

    preset = st.sidebar.selectbox(
        "Product analytics date range",
        ["All time", "Yesterday", "Last 7 days", "This week",
         "This month", "This year", "Custom range"],
        key=f"{key}_preset",
    )

    if preset == "All time":
        return min_date, max_date

    if preset == "Yesterday":
        start = end = today - pd.Timedelta(days=1)
    elif preset == "Last 7 days":
        start, end = today - pd.Timedelta(days=6), today
    elif preset == "This week":
        start, end = today - pd.Timedelta(days=today.weekday()), today
    elif preset == "This month":
        start, end = today.replace(day=1), today
    elif preset == "This year":
        start, end = today.replace(month=1, day=1), today
    else:
        default_start = max(min_date, today - pd.Timedelta(days=29))
        default_end = min(max_date, today)

        selected = st.sidebar.date_input(
            "Choose custom date range",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_custom",
        )

        if not isinstance(selected, (tuple, list)) or len(selected) != 2:
            st.sidebar.caption("Select both a start and end date.")
            return default_start, default_end

        start, end = selected

    return max(start, min_date), min(end, max_date)

def filtered_product_data(start_date, end_date):
    users, events, transactions, _ = load_data()

    return (
        filter_dates(users, "first_open_at", start_date, end_date),
        filter_dates(events, "timestamp", start_date, end_date),
        filter_dates(transactions, "transaction_at", start_date, end_date),
    )

def review_date_filter():
    _, _, _, reviews = load_data()

    valid_dates = reviews["review_date"].dropna()

    if valid_dates.empty:
        today = pd.Timestamp.now(tz=IST).date()
        st.sidebar.warning("No valid review dates were found.")
        return today, today

    min_date = valid_dates.min().tz_convert(IST).date()
    max_date = valid_dates.max().tz_convert(IST).date()

    preset = st.sidebar.selectbox(
        "Review date range",
        ["All review dates", "Last 7 days", "This month",
         "This year", "Custom range"],
        key="review_date_preset",
    )

    today = pd.Timestamp.now(tz=IST).date()

    if preset == "All review dates":
        return min_date, max_date
    elif preset == "Last 7 days":
        start, end = today - pd.Timedelta(days=6), today
    elif preset == "This month":
        start, end = today.replace(day=1), today
    elif preset == "This year":
        start, end = today.replace(month=1, day=1), today
    else:
        selected = st.sidebar.date_input(
            "Choose review dates",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="review_custom_dates",
        )

        if not isinstance(selected, (tuple, list)) or len(selected) != 2:
            return min_date, max_date

        start, end = selected

    start = max(start, min_date)
    end = min(end, max_date)

    if start > end:
        st.sidebar.warning("Invalid review date range.")
        return min_date, max_date

    return start, end

