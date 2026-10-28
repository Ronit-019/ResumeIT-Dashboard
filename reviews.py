import pandas as pd
from google_play_scraper import Sort, reviews_all

APP_ID = 'com.pixsterstudio.resumebuilder'

all_reviews = []

# Fetch using NEWEST sort
print("Fetching NEWEST reviews...")
try:
    r_newest = reviews_all(APP_ID, sleep_milliseconds=50, lang='en', sort=Sort.NEWEST)
    all_reviews.extend(r_newest)
    print(f"Newest batch: {len(r_newest)}")
except Exception as e:
    print(f"Error fetching newest: {e}")

# Fetch using MOST_RELEVANT sort (pulls older top-voted reviews)
print("Fetching MOST_RELEVANT reviews...")
try:
    r_relevant = reviews_all(APP_ID, sleep_milliseconds=50, lang='en', sort=Sort.MOST_RELEVANT)
    all_reviews.extend(r_relevant)
    print(f"Most Relevant batch: {len(r_relevant)}")
except Exception as e:
    print(f"Error fetching relevant: {e}")

# Combine into a single DataFrame & deduplicate by unique reviewId
df = pd.DataFrame(all_reviews)

if not df.empty:
    df = df.drop_duplicates(subset=['reviewId'])
    print(f"\nTotal UNIQUE text reviews fetched: {len(df)}")
    
    csv_name = "resumebuilder_all_reviews.csv"
    df.to_csv(csv_name, index=False)
    print(f"Saved cleanly to '{csv_name}'!")