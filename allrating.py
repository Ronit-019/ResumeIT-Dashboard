from google_play_scraper import app

result = app(
    'com.pixsterstudio.resumebuilder',
    lang='en',
    country='us'
)

# This gives you the official totals behind the '1.33k' count
print("Total Ratings Count:", result['ratings'])
print("Total Reviews Count:", result['reviews'])
print("Star Breakdown Histogram (1 to 5 stars):", result['histogram'])