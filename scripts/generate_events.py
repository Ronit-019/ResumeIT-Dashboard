
from pathlib import Path
import csv
import random
import uuid
from datetime import datetime, timedelta, timezone

SEED = 43
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
USERS_FILE = DATA_DIR / "users.csv"
OUTPUT_FILE = DATA_DIR / "events.csv"

END_DATE = datetime(2026, 10, 27, 23, 59, tzinfo=timezone.utc)

rng = random.Random(SEED)
EVENTS = []

PLAN_PRICES = {
    "Weekly": 99,
    "Yearly": 499,
    "Lifetime": 799,
}


def load_users():
    with USERS_FILE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def add_event(
    user,
    journey,
    name,
    timestamp,
    session_id,
    status="success",
    duration=None,
    plan="",
    amount="",
):
    EVENTS.append({
        "event_id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "session_id": session_id,
        "timestamp": timestamp.isoformat(),
        "journey_name": journey,
        "event_name": name,
        "event_status": status,
        "duration_seconds": (
            duration if duration is not None else ""
        ),
        "plan": plan,
        "amount_inr": amount,
        "is_synthetic": True,
    })


def emit(
    user,
    journey,
    name,
    timestamp,
    session,
    status="success",
):
    add_event(
        user,
        journey,
        name,
        timestamp,
        session,
        status=status,
        duration=rng.randint(2, 90),
    )


def step(
    user,
    journey,
    name,
    timestamp,
    session,
    probability=0.88,
):
    """Emit an event and randomly model abandonment."""
    if rng.random() > probability:
        emit(
            user, journey, name, timestamp, session,
            status="abandoned",
        )
        return False

    emit(user, journey, name, timestamp, session)
    return True


def purchase(user, journey, timestamp, session):
    """Model a paywall purchase attempt."""
    outcome = rng.random()

    if outcome < 0.25:
        plan = rng.choices(
            ["Weekly", "Yearly", "Lifetime"],
            weights=[45, 35, 20],
            k=1,
        )[0]

        emit(
            user, journey, "purchase_succeeded",
            timestamp + timedelta(minutes=2), session,
        )

        # Attach plan and price to the purchase event.
        EVENTS[-1]["plan"] = plan
        EVENTS[-1]["amount_inr"] = PLAN_PRICES[plan]
        return "success"

    if outcome < 0.30:
        plan = rng.choice(list(PLAN_PRICES))

        add_event(
            user,
            journey,
            "purchase_failed",
            timestamp + timedelta(minutes=2),
            session,
            status="failure",
            plan=plan,
            amount=PLAN_PRICES[plan],
        )
        return "failure"

    return "dismissed"


def paywall_with_dismissal(user, journey, timestamp, session):
    """Paywall can be dismissed; payment is not mandatory."""
    emit(user, journey, "paywall_viewed", timestamp, session)

    outcome = purchase(
        user, journey, timestamp + timedelta(minutes=1), session
    )

    if outcome == "dismissed":
        emit(
            user, journey, "paywall_dismissed",
            timestamp + timedelta(minutes=2), session,
        )
    elif outcome == "failure":
        # A failed payment does not prevent the user from
        # closing the paywall and continuing.
        if rng.random() < 0.70:
            emit(
                user, journey, "paywall_dismissed",
                timestamp + timedelta(minutes=3), session,
            )

    return outcome


def allowed_time(timestamp, minutes=15):
    return timestamp + timedelta(minutes=minutes) <= END_DATE


def new_session():
    return str(uuid.uuid4())


def start_journey(user, journey, timestamp):
    session = new_session()
    emit(
        user, journey, "journey_started", timestamp, session
    )
    return session


def resume_export_flow(user, journey, timestamp, session):
    """Model one gated export action: download OR share."""
    action = rng.choice(["download", "share"])

    if action == "download":
        attempted_event = "cv_download_attempted"
        success_event = "cv_download_succeeded"
    else:
        attempted_event = "cv_share_attempted"
        success_event = "cv_share_succeeded"

    if not step(
        user, journey, attempted_event,
        timestamp, session, 0.80,
    ):
        return

    paywall_time = timestamp + timedelta(minutes=1)
    emit(user, journey, "paywall_viewed", paywall_time, session)

    outcome = purchase(
        user, journey, paywall_time + timedelta(minutes=1), session
    )

    if outcome == "success":
        emit(
            user, journey, success_event,
            paywall_time + timedelta(minutes=4), session,
        )
    elif outcome == "dismissed":
        emit(
            user, journey, "paywall_dismissed",
            paywall_time + timedelta(minutes=2), session,
        )
    elif outcome == "failure" and rng.random() < 0.70:
        emit(
            user, journey, "paywall_dismissed",
            paywall_time + timedelta(minutes=3), session,
        )


def resume_editor_flow(user, journey, timestamp, session, prefix=""):
    """Common editor, preview, and gated export flow."""
    if not step(
        user, journey, prefix + "resume_details_entered",
        timestamp + timedelta(minutes=1), session, 0.90,
    ):
        return

    if not step(
        user, journey, prefix + "resume_preview_viewed",
        timestamp + timedelta(minutes=2), session, 0.90,
    ):
        return

    resume_export_flow(
        user, journey, timestamp + timedelta(minutes=3), session
    )


def create_or_upload_branch(user, journey, timestamp, session):
    """Choose Create or Upload, then continue through preview and export."""
    if not step(
        user, journey, "create_resume_or_upload_shown",
        timestamp, session, 0.95,
    ):
        return

    branch = rng.choice(["create", "upload"])

    if branch == "create":
        if step(
            user, journey, "create_resume_selected",
            timestamp + timedelta(seconds=30), session, 0.90,
        ):
            resume_editor_flow(
                user, journey,
                timestamp + timedelta(minutes=1), session,
            )
    else:
        if not step(
            user, journey, "upload_resume_selected",
            timestamp + timedelta(seconds=30), session, 0.90,
        ):
            return

        if not step(
            user, journey, "resume_upload_attempted",
            timestamp + timedelta(minutes=1), session, 0.90,
        ):
            return

        if not step(
            user, journey, "resume_parse_succeeded",
            timestamp + timedelta(minutes=2), session, 0.88,
        ):
            return

        resume_editor_flow(
            user, journey,
            timestamp + timedelta(minutes=2), session,
        )


def create_or_upload_branch(user, journey, timestamp, session):
    """The paywall can be dismissed before choosing either option."""
    if not step(
        user, journey, "create_resume_or_upload_shown",
        timestamp, session, 0.95,
    ):
        return

    branch = rng.choice(["create", "upload"])

    if branch == "create":
        if step(
            user, journey, "create_resume_selected",
            timestamp + timedelta(seconds=30), session, 0.90,
        ):
            resume_editor_flow(
                user, journey,
                timestamp + timedelta(minutes=1), session,
            )
    else:
        if step(
            user, journey, "upload_resume_selected",
            timestamp + timedelta(seconds=30), session, 0.90,
        ):
            if step(
                user, journey, "resume_upload_attempted",
                timestamp + timedelta(minutes=1), session, 0.90,
            ):
                if step(
                    user, journey, "resume_parse_succeeded",
                    timestamp + timedelta(minutes=2), session, 0.88,
                ):
                    if step(
                        user, journey, "resume_details_entered",
                        timestamp + timedelta(minutes=3), session, 0.90,
                    ):
                        step(
                            user, journey, "resume_preview_viewed",
                            timestamp + timedelta(minutes=4), session, 0.90,
                        )


def onboarding(user, first_open):
    """Generate one of the three complete goal-based onboarding journeys."""
    if rng.random() > 0.88:
        return

    goal = rng.choices(
        [
            "create_first_resume",
            "improve_existing_resume",
            "write_cover_letter",
        ],
        weights=[0.45, 0.30, 0.25],
        k=1,
    )[0]

    journey_names = {
        "create_first_resume": "Onboarding - Create My First Resume",
        "improve_existing_resume": "Onboarding - Improve Existing Resume",
        "write_cover_letter": "Onboarding - Write a Cover Letter",
    }
    journey = journey_names[goal]
    session = new_session()
    t = first_open

    # Shared onboarding steps are recorded under the selected goal journey,
    # so each of the three onboarding funnels includes the complete entry path.
    emit(user, journey, "first_app_open", t, session)

    if not step(
        user, journey, "welcome_screen_viewed",
        t + timedelta(seconds=3), session, 0.98,
    ):
        return

    if not step(
        user, journey, "create_resume_tapped",
        t + timedelta(seconds=8), session, 0.90,
    ):
        return

    if not step(
        user, journey, "experience_selected",
        t + timedelta(seconds=15), session, 0.90,
    ):
        return

    add_event(
        user,
        journey,
        "goal_selected",
        t + timedelta(seconds=22),
        session,
        plan=goal,
        duration=rng.randint(2, 90),
    )

    if rng.random() < 0.80:
        emit(
            user, journey, "onboarding_completed",
            t + timedelta(seconds=30), session,
        )

    branch_time = t + timedelta(minutes=1)

    if goal == "create_first_resume":
        if step(
            user, journey, "template_selected",
            branch_time + timedelta(seconds=20), session, 0.90,
        ):
            # Initial template-selection paywall; dismissing it still
            # allows the user to continue to Create/Upload.
            paywall_with_dismissal(
                user, journey, branch_time + timedelta(minutes=1), session
            )
            create_or_upload_branch(
                user, journey, branch_time + timedelta(minutes=4), session
            )

    elif goal == "improve_existing_resume":
        if not step(
            user, journey, "resume_upload_attempted",
            branch_time + timedelta(seconds=20), session, 0.90,
        ):
            return

        if not step(
            user, journey, "resume_parse_succeeded",
            branch_time + timedelta(minutes=1), session, 0.88,
        ):
            return

        if not step(
            user, journey, "template_selected",
            branch_time + timedelta(minutes=2), session, 0.90,
        ):
            return

        resume_editor_flow(
            user, journey, branch_time + timedelta(minutes=2), session
        )

    else:
        cover_letter_flow(
            user, journey, branch_time, session=session
        )


def cover_letter_flow(user, journey, timestamp, session=None):
    """Shared cover-letter flow. Export is free; AI rewrite is optional."""
    if session is None:
        session = start_journey(user, journey, timestamp)

    steps = [
        ("cover_template_selected", 0.92),
        ("cover_template_previewed", 0.92),
        ("sender_details_entered", 0.90),
        ("letter_summary_entered", 0.88),
        ("receiver_details_entered", 0.88),
        ("cover_letter_details_reviewed", 0.92),
        ("cover_letter_preview_viewed", 0.92),
        ("cover_letter_export_attempted", 0.85),
    ]

    for i, (name, probability) in enumerate(steps, start=1):
        if not step(
            user, journey, name,
            timestamp + timedelta(minutes=i), session, probability,
        ):
            return

        if name == "letter_summary_entered":
            # AI rewrite is available only at 50 words or more.
            simulated_word_count = rng.randint(20, 100)

            if simulated_word_count >= 50 and rng.random() < 0.30:
                rewrite_time = timestamp + timedelta(minutes=i)
                emit(
                    user, journey, "ai_rewrite_eligible",
                    rewrite_time + timedelta(seconds=5), session,
                )

                if step(
                    user, journey, "cover_letter_ai_rewrite_selected",
                    rewrite_time + timedelta(seconds=10), session, 0.65,
                ):
                    if rng.random() < 0.90:
                        emit(
                            user, journey, "cover_letter_ai_rewrite_succeeded",
                            rewrite_time + timedelta(seconds=20), session,
                        )

    if rng.random() < 0.97:
        emit(
            user, journey, "cover_letter_export_succeeded",
            timestamp + timedelta(minutes=9), session,
        )


def ats_flow(user, timestamp, journey="Home - Check ATS Score"):
    """Generate ATS scoring and its Find Fixes/Rescan/Exit branches."""
    session = start_journey(user, journey, timestamp)

    if not step(
        user, journey, "ats_resume_upload_started",
        timestamp + timedelta(seconds=20), session, 0.90,
    ):
        return

    if not step(
        user, journey, "ats_resume_submitted",
        timestamp + timedelta(minutes=1), session, 0.90,
    ):
        return

    if not step(
        user, journey, "ats_analysis_started",
        timestamp + timedelta(minutes=2), session, 0.95,
    ):
        return

    if not step(
        user, journey, "ats_score_displayed",
        timestamp + timedelta(minutes=3), session, 0.90,
    ):
        return

    branch = rng.choices(
        ["find_fixes", "rescan", "exit"],
        weights=[0.45, 0.35, 0.20],
        k=1,
    )[0]

    if branch == "find_fixes":
        steps = [
            ("ats_find_fixes_selected", 0.90),
            ("resume_fixes_viewed", 0.90),
            ("fix_my_resume_selected", 0.80),
            ("resume_fixes_preparing", 0.95),
            ("resume_improvement_review_viewed", 0.90),
        ]

        for i, (name, probability) in enumerate(steps, start=1):
            if not step(
                user, journey, name,
                timestamp + timedelta(minutes=3 + i), session, probability,
            ):
                return

        choice = rng.choice(["now", "later"])
        if choice == "now":
            emit(
                user, journey, "resume_improvement_now_selected",
                timestamp + timedelta(minutes=9), session,
            )
            emit(
                user, journey, "resume_editor_opened",
                timestamp + timedelta(minutes=10), session,
            )
        else:
            emit(
                user, journey, "resume_improvement_later_selected",
                timestamp + timedelta(minutes=9), session,
            )

    elif branch == "rescan":
        t = timestamp + timedelta(minutes=4)
        emit(user, journey, "ats_rescan_selected", t, session)

        if not step(
            user, journey, "ats_resume_upload_started",
            t + timedelta(seconds=30), session, 0.90,
        ):
            return
        if not step(
            user, journey, "ats_resume_submitted",
            t + timedelta(minutes=1), session, 0.90,
        ):
            return
        if not step(
            user, journey, "ats_analysis_started",
            t + timedelta(minutes=2), session, 0.95,
        ):
            return
        step(
            user, journey, "ats_score_displayed",
            t + timedelta(minutes=3), session, 0.90,
        )


def ai_resume_flow(user, timestamp):
    journey = "Home - AI Resume"
    session = start_journey(user, journey, timestamp)

    emit(
        user, journey, "ai_resume_tapped",
        timestamp + timedelta(seconds=5), session,
    )
    emit(
        user, journey, "paywall_viewed",
        timestamp + timedelta(seconds=6), session,
    )

    outcome = purchase(
        user, journey, timestamp + timedelta(seconds=10), session
    )

    if outcome == "dismissed":
        emit(
            user, journey, "paywall_dismissed",
            timestamp + timedelta(seconds=20), session,
        )
    elif outcome == "failure" and rng.random() < 0.70:
        emit(
            user, journey, "paywall_dismissed",
            timestamp + timedelta(seconds=30), session,
        )

    # Post-payment AI generation remains unspecified until confirmed.


def quick_mail_flow(user, timestamp):
    journey = "Home - Send Quick Mail"
    session = start_journey(user, journey, timestamp)

    steps = [
        ("mail_composer_opened", 0.95),
        ("recruiter_email_entered", 0.90),
        ("resume_pdf_uploaded", 0.88),
        ("recruiter_message_entered", 0.88),
        ("linkedin_url_entered", 0.80),
        ("mail_send_tapped", 0.85),
    ]

    for i, (name, probability) in enumerate(steps, start=1):
        if not step(
            user, journey, name,
            timestamp + timedelta(minutes=i), session, probability,
        ):
            return

    # Gmail opening is a handoff, not proof that an email was sent.
    if rng.random() < 0.95:
        emit(
            user, journey, "gmail_draft_opened",
            timestamp + timedelta(minutes=7), session,
        )


def returning_user_journeys(user, first_open):
    journeys = [
        ("Home - Create or Upload Resume", 0.48),
        ("Home - Resume Templates", 0.22),
        ("Home - Check ATS Score", 0.35),
        ("Home - AI Resume", 0.20),
        ("Home - Cover Letter", 0.25),
        ("Home - Send Quick Mail", 0.12),
    ]

    selected = [
        name for name, probability in journeys
        if rng.random() < probability
    ]

    for index, journey in enumerate(selected):
        timestamp = first_open + timedelta(
            days=rng.randint(1, 60),
            hours=rng.randint(0, 12),
        ) + timedelta(minutes=index * 15)

        if not allowed_time(timestamp, 15):
            continue

        if journey == "Home - Create or Upload Resume":
            session = start_journey(user, journey, timestamp)
            if step(
                user, journey, "template_selected",
                timestamp + timedelta(minutes=1), session, 0.90,
            ):
                create_or_upload_branch(
                    user, journey, timestamp + timedelta(minutes=2), session
                )

        elif journey == "Home - Resume Templates":
            session = start_journey(user, journey, timestamp)
            if not step(
                user, journey, "resume_templates_viewed",
                timestamp + timedelta(seconds=10), session, 0.95,
            ):
                continue

            # See All is optional; users can choose a featured template.
            if rng.random() < 0.65:
                emit(
                    user, journey, "resume_templates_see_all_tapped",
                    timestamp + timedelta(seconds=30), session,
                )

            if step(
                user, journey, "template_selected",
                timestamp + timedelta(minutes=1), session, 0.90,
            ):
                create_or_upload_branch(
                    user, journey, timestamp + timedelta(minutes=2), session
                )

        elif journey == "Home - Check ATS Score":
            ats_flow(user, timestamp, journey)

        elif journey == "Home - AI Resume":
            ai_resume_flow(user, timestamp)

        elif journey == "Home - Cover Letter":
            cover_letter_flow(user, journey, timestamp)

        elif journey == "Home - Send Quick Mail":
            quick_mail_flow(user, timestamp)


def main():
    users = load_users()

    if not users:
        raise ValueError(f"No users found in {USERS_FILE}")

    for user in users:
        first_open = datetime.fromisoformat(user["first_open_at"])

        # Normalize naive timestamps to UTC.
        if first_open.tzinfo is None:
            first_open = first_open.replace(tzinfo=timezone.utc)

        onboarding(user, first_open)

        # Simulate returning activity for a subset of users.
        if rng.random() < 0.58:
            returning_user_journeys(user, first_open)

    EVENTS.sort(key=lambda row: row["timestamp"])

    fieldnames = [
        "event_id",
        "user_id",
        "session_id",
        "timestamp",
        "journey_name",
        "event_name",
        "event_status",
        "duration_seconds",
        "plan",
        "amount_inr",
        "is_synthetic",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(EVENTS)

    print(f"Generated {len(EVENTS):,} events: {OUTPUT_FILE}")
    print(f"Users processed: {len(users):,}")
    print("All behavioral data is synthetic and illustrative.")


if __name__ == "__main__":
    main()
