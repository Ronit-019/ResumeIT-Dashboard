import pandas as pd
from textblob import TextBlob

# Load your reviews dataset
df = pd.read_csv("app_reviews.csv")

# Function to get polarity score
def get_sentiment_score(text):
    if pd.isna(text):
        return 0.0
    return TextBlob(str(text)).sentiment.polarity

# Function to label sentiment category
def get_sentiment_label(score):
    if score > 0.1:
        return 'Positive'
    elif score < -0.1:
        return 'Negative'
    else:
        return 'Neutral'

# Apply functions to your dataset
df['polarity'] = df['content'].apply(get_sentiment_score)
df['sentiment'] = df['polarity'].apply(get_sentiment_label)

# View the breakdown
print(df['sentiment'].value_counts())

# Save the results to a new CSV file
df.to_csv("app_reviews_with_sentiment.csv", index=False)