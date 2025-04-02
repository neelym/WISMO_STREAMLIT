import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import os
import logging
import re

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_snowflake_session():
    """Create a persistent Snowflake session"""
    conn = st.connection("Wismo")
    session = conn.session()
    logger.info("Session SUCCESSFULLY started...")
    return session

# Include Poppins font from Google Fonts
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True,
)

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"]  {
            font-family: 'Poppins', sans-serif;
        }
        .centered-text {
            text-align: center;
        }
        .bold-number {
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        .metric-title {
            color: #737373;
            text-align: center;
            margin-bottom: 0px; /* Remove default bottom margin */
        }
        .metric-number {
            color: #000;
            text-align: center;
            margin-top: 0px;    /* Remove default top margin */
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# Function to fetch sentiment data from Snowflake
def fetch_sentiment_data(session,customer_id):
    if not re.match(r"^CUST-\d+$", customer_id):
        raise ValueError("Invalid customer ID format.")
    
    query = f"""
    WITH SentimentBucketCounts AS (
        SELECT
            CONVERSATION_ID,
            CALL_DATE,
            sentiment_bucket,
            COUNT(*) AS bucket_line_count
        FROM CALL_TRANSCRIPTS
        WHERE IS_CUSTOMER = 'TRUE'
        GROUP BY CONVERSATION_ID, CALL_DATE, sentiment_bucket
    ),
    TotalCustomerLinesPerConversation AS (
        SELECT
            CONVERSATION_ID,
            COUNT(*) AS total_customer_lines
        FROM CALL_TRANSCRIPTS
        WHERE IS_CUSTOMER = 'TRUE' AND SPEAKER_ID = '{customer_id}'
        GROUP BY CONVERSATION_ID
    )
    SELECT
        sbc.CONVERSATION_ID,
        sbc.CALL_DATE,
        sbc.sentiment_bucket,
        sbc.bucket_line_count,
        tlpc.total_customer_lines,
        (sbc.bucket_line_count * 100.0) / tlpc.total_customer_lines AS percentage
    FROM SentimentBucketCounts sbc
    JOIN TotalCustomerLinesPerConversation tlpc ON sbc.CONVERSATION_ID = tlpc.CONVERSATION_ID
    ORDER BY sbc.CONVERSATION_ID, sbc.sentiment_bucket;
    """
    
    try:
        df = session.sql(query).to_pandas()
        print("Data from Snowflake:")  # Add this line
        print(df)  # And this line
        return df
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        st.error("Failed to fetch sentiment data from Snowflake.")
        return pd.DataFrame()
    
# --- Function to plot sentiment data ---
def plot_sentiment_chart(sentiment_data):
    sentiment_mapping = {
        "Very Negative": "#ef6658",
        "Negative": "#efad56",  # Changed from "#F0AD4E" to match the visual
        "Neutral": "#b0ccca",  # Changed from "#FFD700" to match the visual
        "Positive": "#53a69a",  # Changed from "#5CB85C" to match the visual
        "Very Positive": "#63b075",  # Changed from "#2E8B57" to match the visual
    }

    # Ensure column names match case sensitivity
    sentiment_data.columns = [col.lower() for col in sentiment_data.columns]

    if "sentiment_bucket" not in sentiment_data.columns:
        st.error("Error: 'sentiment_bucket' column not found in query results.")
        return None

    sentiment_data['call_date'] = pd.to_datetime(sentiment_data['call_date'])
    sentiment_data["sentiment_bucket"] = sentiment_data["sentiment_bucket"].replace({
    "Slightly Negative": "Negative",
    "Very Negative": "Very Negative",  # Optional, you can include others too
    # Add more mappings as needed
    })

    conversation_date_mapping = sentiment_data.set_index('conversation_id')['call_date'].drop_duplicates()

    # Pivot DataFrame to get stacked values for bar chart
    pivot_df = sentiment_data.pivot(index="conversation_id", columns="sentiment_bucket", values="percentage").fillna(0)

    fig, ax = plt.subplots(figsize=(10, 2.8))  # Increased figsize to take more width

    # Create stacked horizontal bar chart
    bottom = None
    for sentiment in sentiment_mapping.keys():
        if sentiment in pivot_df:
            ax.barh(pivot_df.index, pivot_df[sentiment], left=bottom, color=sentiment_mapping[sentiment], label=sentiment)
            bottom = pivot_df[sentiment] if bottom is None else bottom + pivot_df[sentiment]

    ax.set_xlim(0, 100)
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.tick_params(left=False, bottom=False)
    ax.set_xticks([])
    ax.set_yticklabels(conversation_date_mapping[pivot_df.index].dt.strftime('%m/%d/%Y'), fontsize=12, color='#555')
    ax.invert_yaxis()
    ax.spines[['top', 'right', 'left', 'bottom']].set_visible(False)

    return fig
    
def calculate_total_bucket_score(sentiment_data, sentiment_weights):
    total_bucket_score = 0
    for index, row in sentiment_data.iterrows():
        sentiment = row["sentiment_bucket"]
        weight = sentiment_weights.get(sentiment, 0)  # Get the weight, default to 0 if not found
        bucket_line_count = row["bucket_line_count"]
        total_bucket_score += weight * bucket_line_count  # Multiply weight by count
    return total_bucket_score

def calculate_sentiment_score(total_bucket_score, sentiment_data, sentiment_weights):
    # Get unique conversation IDs
    unique_conversations = sentiment_data["conversation_id"].unique()

    # Calculate the sum of total_customer_lines for each unique conversation
    total_customer_lines = 0
    for conversation_id in unique_conversations:
        # Assuming total_customer_lines is constant for a given conversation
        total_customer_lines += sentiment_data[sentiment_data["conversation_id"] == conversation_id]["total_customer_lines"].iloc[0]

    perfect_score = total_customer_lines * 5 # Or use total lines if appropriate
    if perfect_score > 0:
        sentiment_score = int((total_bucket_score / perfect_score) * 100)
    else:
        sentiment_score = 0
    return sentiment_score

# --- LAYOUT ---
st.markdown("""
<h2 style="margin-bottom: 0.2rem;">Sentiment Analysis</h2>
<div style="height: 4px; width: 100px; background-color: #0073e6; margin-bottom: 10px;"></div>
<hr style="margin-top: -10px;">
""", unsafe_allow_html=True)

# Get URL query parameters
query_params = st.query_params
customer_id = query_params.get("customer_id")
print(customer_id)

if not customer_id: 
    customer_id = "CUST-0001"

if customer_id:
    session = get_snowflake_session()
    if session: 
        sentiment_data = fetch_sentiment_data(session,customer_id)
        sentiment_data.columns = [col.lower() for col in sentiment_data.columns]  # Convert all column names to lowercase
       
        if not sentiment_data.empty:
            sentiment_weights = {
                    "Very Negative": 1,
                    "Negative": 2,
                    "Neutral": 3,
                    "Positive": 4,
                    "Very Positive": 5,
                }

            total_bucket_score = calculate_total_bucket_score(sentiment_data, sentiment_weights)
            print(total_bucket_score)
            sentiment_score = calculate_sentiment_score(total_bucket_score, sentiment_data, sentiment_weights)
            # --- Call Total and Sentiment Score ---
            col1, col2 = st.columns(2)
            with col1:
                call_total = sentiment_data["conversation_id"].nunique()
                st.markdown("<h6 style='color: #737373; text-align: center; margin-bottom: -20px;'>Call Total</h6>", unsafe_allow_html=True)
                st.markdown(f"<h1 style='color:#000; text-align: center; margin-top: -20px; font-weight: bold;'>{call_total}</h1>", unsafe_allow_html=True)

            with col2:
                # Custom logic for computing sentiment score (adapt to your needs)
                positive_sentiment = sentiment_data[sentiment_data["sentiment_bucket"].isin(["Positive", "Very Positive"])]
                total_percentage = sentiment_data["percentage"].sum()
                st.markdown("<h6 style='color: #737373; text-align: center; margin-bottom: -20px;'>Sentiment Score</h6>", unsafe_allow_html=True)
                st.markdown(f"<h1 style='color:#000; text-align: center; margin-top: -20px; font-weight: bold;'>{sentiment_score}%</h1>", unsafe_allow_html=True)

            # --- Chart Explanation ---
            st.markdown("""
            <div style='margin-top: 15px; margin-bottom: 15px; font-size: 0.9rem; color: #555; font-style: italic; text-align: center;'>
            This line chart depicts the real-time shift in sentiment categories from a customer—ranging from very negative to very positive—as an agent interacts with a customer throughout the duration of a single call.
            </div>
            """, unsafe_allow_html=True)

            # --- Sentiment Bar Chart ---
            st.pyplot(plot_sentiment_chart(sentiment_data), use_container_width=True)

            # --- Custom Legend ---
            st.markdown("""
            <div style='margin-top: 10px;'>
                <div style='font-size: large; color: #555; margin-bottom: 5px;'>Sentiment</div>
                <div style='display: flex; flex-direction: column; align-items: flex-start;'>
                    <div style='display: flex; align-items: center; margin-bottom: 3px;'>
                        <div style='width: 20px; height: 20px; background-color: #ef6658; margin-right: 5px;'></div>
                        <div style='font-size: medium; color: #555;'>Very Negative</div>
                    </div>
                    <div style='display: flex; align-items: center; margin-bottom: 3px;'>
                        <div style='width: 20px; height: 20px; background-color: #efad56; margin-right: 5px;'></div>
                        <div style='font-size: medium; color: #555;'>Negative</div>
                    </div>
                    <div style='display: flex; align-items: center; margin-bottom: 3px;'>
                        <div style='width: 20px; height: 20px; background-color: #b0ccca; margin-right: 5px;'></div>
                        <div style='font-size: medium; color: #555;'>Neutral</div>
                    </div>
                    <div style='display: flex; align-items: center; margin-bottom: 3px;'>
                        <div style='width: 20px; height: 20px; background-color: #53a69a; margin-right: 5px;'></div>
                        <div style='font-size: medium; color: #555;'>Positive</div>
                    </div>
                    <div style='display: flex; align-items: center;'>
                        <div style='width: 20px; height: 20px; background-color: #63b075; margin-right: 5px;'></div>
                        <div style='font-size: medium; color: #555;'>Very Positive</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No data found")

