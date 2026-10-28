
from pathlib import Path
import csv
import random
import uuid
from datetime import datetime, timedelta, timezone

SEED = 42
NUM_USERS = 1500
END_DATE = datetime(2026, 10, 27, 23, 59, tzinfo=timezone.utc)
START_DATE = END_DATE - timedelta(days=179)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

rng = random.Random(SEED)

sources = ["Organic Search", "Play Store", "Social Media", "Referral", "Paid Ads"]
source_weights = [30, 25, 18, 15, 12]

rows = []

for i in range(1, NUM_USERS + 1):
    seconds = int((END_DATE - START_DATE).total_seconds())
    first_open = START_DATE + timedelta(seconds=rng.randint(0, seconds))

    rows.append({
        "user_id": f"user_{i:05d}",
        "first_open_at": first_open.isoformat(),
        "acquisition_source": rng.choices(
            sources, weights=source_weights, k=1
        )[0],
        "platform": "Android",
        "is_synthetic": True,
    })

path = DATA_DIR / "users.csv"

with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows):,} users: {path}")
