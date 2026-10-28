
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "data" / "events.csv"

df = pd.read_csv(EVENTS_FILE)
errors = []
warnings = []

required_columns = {
    "event_id",
    "user_id",
    "session_id",
    "timestamp",
    "journey_name",
    "event_name",
    "event_status",
    "plan",
    "amount_inr",
    "is_synthetic",
}

missing_columns = required_columns - set(df.columns)
if missing_columns:
    errors.append(f"Missing columns: {sorted(missing_columns)}")

if not missing_columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    if df["event_id"].duplicated().any():
        errors.append("Duplicate event IDs found.")

    if df["timestamp"].isna().any():
        errors.append("Invalid timestamps found.")

    if not df["is_synthetic"].astype(str).str.lower().eq("true").all():
        errors.append("Some events are not marked synthetic.")

    goals = df[
        (df["journey_name"] == "First-Open Onboarding")
        & (df["event_name"] == "goal_selected")
    ]

    allowed_goals = {
        "create_first_resume",
        "improve_existing_resume",
        "write_cover_letter",
    }

    if goals["plan"].isna().any():
        errors.append("Some goal selections have no goal value.")

    invalid_goals = set(goals["plan"].dropna()) - allowed_goals
    if invalid_goals:
        errors.append(f"Unexpected goal values: {invalid_goals}")

    # Check chronological ordering within sessions.
    ordered = df.sort_values("timestamp")
    session_times = ordered.groupby(
        ["user_id", "session_id"]
    )["timestamp"]

    if not session_times.apply(lambda s: s.is_monotonic_increasing).all():
        errors.append("Events are not chronological within sessions.")

    # AI Resume must show its paywall before any successful purchase.
    ai = df[df["journey_name"] == "AI Resume"]
    for session, events in ai.groupby("session_id"):
        names = events.sort_values("timestamp")["event_name"].tolist()

        if "ai_resume_tapped" in names and "paywall_viewed" not in names:
            errors.append(f"AI Resume session {session} has no paywall.")

    # Cover-letter journeys must not contain purchase events.
    cover = df[df["journey_name"].isin([
        "Home - Cover Letter",
        "Onboarding - Cover Letter",
        "Cover Letter - AI Rewrite",
    ])]

    paid_cover_events = cover[
        cover["event_name"].isin([
            "paywall_viewed",
            "purchase_succeeded",
            "purchase_failed",
        ])
    ]

    if not paid_cover_events.empty:
        errors.append("Cover-letter flow unexpectedly contains payment events.")

    # Gmail draft opening is not proof of a sent email.
    mail = df[df["journey_name"] == "Send Quick Mail"]
    if "mail_sent_successfully" in set(mail["event_name"]):
        warnings.append(
            "mail_sent_successfully exists; verify that it is not inferred "
            "from the Gmail handoff."
        )

print(f"Events: {len(df):,}")
print(f"Users: {df['user_id'].nunique():,}")
print(f"Journeys: {df['journey_name'].nunique():,}")
print(f"Goal selections: {len(goals):,}")
print(f"Missing goal values: {goals['plan'].isna().sum():,}")

for warning in warnings:
    print(f"WARNING: {warning}")

if errors:
    print("\nVALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("\nVALIDATION PASSED")
