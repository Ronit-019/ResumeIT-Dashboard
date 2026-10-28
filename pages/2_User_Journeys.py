import pandas as pd
import plotly.express as px
import streamlit as st

from analysis.journeys import JOURNEY_STEPS
from dashboard_common import date_filter, filtered_product_data

st.set_page_config(
    page_title="User Journeys",
    page_icon="🔀",
    layout="wide",
)

st.title("User Journey Analysis")
st.caption(
    "Explore sequential conversion and drop-offs across product journeys. "
    "Usage events are synthetic and illustrative."
)

start_date, end_date = date_filter()
_, events, _ = filtered_product_data(start_date, end_date)
st.caption(f"Period: {start_date:%d %b %Y} – {end_date:%d %b %Y}")

required_columns = {
    "user_id", "session_id", "timestamp", "journey_name", "event_name"
}
if not required_columns.issubset(events.columns):
    st.error("The events dataset is missing required funnel columns.")
    st.stop()

events = events.copy()
events["timestamp"] = pd.to_datetime(
    events["timestamp"], utc=True, errors="coerce"
)
events = events.dropna(
    subset=["user_id", "session_id", "timestamp", "journey_name", "event_name"]
)

journey_options = list(JOURNEY_STEPS)
if not journey_options:
    st.error("No journeys are configured in analysis/journeys.py.")
    st.stop()

journey = st.selectbox("Select journey", journey_options)
steps = JOURNEY_STEPS[journey]

journey_events = events.loc[events["journey_name"] == journey].sort_values(
    "timestamp"
)

if journey_events.empty:
    st.info("No events were recorded for this journey in the selected period.")
    st.stop()


def calculate_sequential_funnel(data, step_names):
    """Count sessions reaching each ordered step; repeated names are supported."""
    if not step_names:
        return []

    sequences = [
        group.sort_values("timestamp")["event_name"].tolist()
        for _, group in data.groupby(["user_id", "session_id"], sort=False)
    ]

    counts = []
    for step_index in range(len(step_names)):
        reached = 0
        prefix = step_names[: step_index + 1]
        for sequence in sequences:
            matched = 0
            for event_name in sequence:
                if event_name == prefix[matched]:
                    matched += 1
                    if matched == len(prefix):
                        reached += 1
                        break
        counts.append(reached)
    return counts


# Branch-aware display steps: optional steps are not treated as mandatory.
# This makes the overall funnel useful without pretending every user follows
# the same branch. Detailed branch outcomes are shown separately below.
OPTIONAL_STEPS = {
    "Home - Resume Templates": {"resume_templates_see_all_tapped"},
}
steps_for_funnel = [
    step for step in steps
    if step not in OPTIONAL_STEPS.get(journey, set())
]
counts = calculate_sequential_funnel(journey_events, steps_for_funnel)

rows = []
previous_count = None
for event_name, count in zip(steps_for_funnel, counts):
    conversion = (
        count / previous_count * 100
        if previous_count
        else (100.0 if count else 0.0)
    )
    dropoff = (
        max(previous_count - count, 0)
        if previous_count is not None
        else 0
    )
    rows.append({
        "Step": event_name.replace("_", " ").title(),
        "Event Name": event_name,
        "Sessions Reached": int(count),
        "Step Conversion (%)": round(conversion, 1),
        "Drop-off (sessions)": int(dropoff),
    })
    previous_count = count

funnel = pd.DataFrame(rows)
entrants = int(funnel.iloc[0]["Sessions Reached"])
completions = int(funnel.iloc[-1]["Sessions Reached"])
completion_rate = completions / entrants * 100 if entrants else 0.0

a, b, c = st.columns(3)
a.metric("Journey Entrants", f"{entrants:,}")
b.metric("Final-Step Sessions", f"{completions:,}")
c.metric("Overall Completion", f"{completion_rate:.1f}%")

if entrants:
    fig = px.funnel(
        funnel,
        x="Sessions Reached",
        y="Step",
        title=f"{journey} — Sequential Funnel",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        funnel.drop(columns=["Event Name"]),
        use_container_width=True,
        hide_index=True,
    )

    later_steps = funnel.iloc[1:]
    if not later_steps.empty:
        biggest_drop = later_steps.sort_values(
            "Drop-off (sessions)", ascending=False
        ).iloc[0]
        st.info(
            "Largest sequential drop-off: "
            f"**{biggest_drop['Step']}** "
            f"({int(biggest_drop['Drop-off (sessions)']):,} sessions)."
        )
else:
    st.info("No sessions reached the first funnel step in this period.")

# Show branch/outcome counts as event occurrences, not as a linear funnel.
BRANCH_EVENTS = {
    "Home - Create or Upload Resume": [
        "create_resume_selected", "upload_resume_selected",
        "cv_download_succeeded", "cv_share_succeeded",
        "paywall_dismissed", "purchase_failed",
    ],
    "Home - Resume Templates": [
        "resume_templates_see_all_tapped", "create_resume_selected",
        "upload_resume_selected",
    ],
    "Home - Check ATS Score": [
        "ats_find_fixes_selected", "ats_rescan_selected",
        "resume_improvement_now_selected", "resume_improvement_later_selected",
    ],
    "Home - AI Resume": [
        "purchase_succeeded", "purchase_failed", "paywall_dismissed",
    ],
    "Onboarding - Create My First Resume": [
        "create_resume_selected", "upload_resume_selected",
        "cv_download_succeeded", "cv_share_succeeded",
        "paywall_dismissed", "purchase_failed",
    ],
}
branch_events = BRANCH_EVENTS.get(journey, [])
if branch_events:
    st.subheader("Branch and outcome activity")
    branch_rows = []
    for event_name in branch_events:
        event_count = int((journey_events["event_name"] == event_name).sum())
        branch_rows.append({
            "Event": event_name.replace("_", " ").title(),
            "Event occurrences": event_count,
        })
    st.dataframe(
        pd.DataFrame(branch_rows),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Branch/outcome counts are event occurrences, not unique sessions or "
        "sequential funnel counts. A session may contribute to multiple rows."
    )

st.caption(
    "Method: sequential counts require each displayed step in timestamp order. "
    "Optional steps are excluded from the required funnel; alternative branch "
    "events are reported separately. Data is synthetic and illustrative, not "
    "real app telemetry."
)
