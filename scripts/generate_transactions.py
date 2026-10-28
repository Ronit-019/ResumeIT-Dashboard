
from pathlib import Path
import csv
import uuid

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EVENTS_FILE = DATA_DIR / "events.csv"
OUTPUT_FILE = DATA_DIR / "transactions.csv"

if not EVENTS_FILE.exists():
    raise FileNotFoundError(
        f"{EVENTS_FILE} not found. Run generate_events.py first."
    )

transactions = []

with EVENTS_FILE.open(encoding="utf-8", newline="") as f:
    for event in csv.DictReader(f):
        event_name = event["event_name"]

        if event_name not in ("purchase_succeeded", "purchase_failed"):
            continue

        success = event_name == "purchase_succeeded"

        transactions.append({
            "transaction_id": str(uuid.uuid4()),
            "source_event_id": event["event_id"],
            "user_id": event["user_id"],
            "transaction_at": event["timestamp"],
            "journey_name": event["journey_name"],
            "plan": event["plan"],
            "price_inr": float(event["amount_inr"] or 0),
            "payment_status": "success" if success else "failed",
            "recognized_revenue_inr": (
                float(event["amount_inr"] or 0) if success else 0
            ),
            "is_synthetic": True,
        })

# Keep output deterministic in ordering.
transactions.sort(key=lambda row: row["transaction_at"])

with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
    if transactions:
        writer = csv.DictWriter(
            f, fieldnames=transactions[0].keys()
        )
        writer.writeheader()
        writer.writerows(transactions)
    else:
        print("No purchase events were generated.")

print(f"Generated {len(transactions):,} transaction records: {OUTPUT_FILE}")
print(
    "Successful purchases:",
    sum(t["payment_status"] == "success" for t in transactions)
)
print(
    "Illustrative revenue (INR):",
    sum(t["recognized_revenue_inr"] for t in transactions)
)
