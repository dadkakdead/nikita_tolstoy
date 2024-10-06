from telethon import TelegramClient
from telethon.sessions import StringSession
import openai
import requests
import json
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import re

from decouple import config

# Read Telegram credentials stored as JSON in environment variable
telegram_credentials = json.loads(config('FOCUS_NEWS_TG_CREDS'))  # Updated

# Extract the individual credentials with lower case parameter names
api_id = telegram_credentials['api_id']
api_hash = telegram_credentials['api_hash']
session_string = telegram_credentials['session_string']

# Initialize Telegram Client with session string
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Database connection parameters
connection_string = config('FOCUS_NEWS_DB')

# Channel to send log messages
LOG_CHANNEL_ID = <LOG_CHANNEL_ID>  # ID of the 'Фокус News Logs' channel

# Channel to send reports
NEWS_CHANNEL_ID = <NEWS_CHANNEL_ID>  # ID of the 'Фокус News: Лавка' channel

openai.api_key = config('FOCUS_NEWS_OPENAI_API_KEY')

# Step 1: Query the news from the last week
def query_news_last_week(connection_string):
    # Current date and time
    now = datetime.now()
    # Calculate the date and time for one week ago
    one_week_ago = now - timedelta(days=7)

    # Create a database engine connection
    engine = create_engine(connection_string)

    # SQL query to get news from the last week
    query = f"""
    SELECT id, content, links, message_date, views, reactions_count, comments_count
    FROM news
    WHERE message_date >= '{one_week_ago.strftime('%Y-%m-%d %H:%M:%S')}'
    """

    # Read the query results into a pandas DataFrame
    news_df = pd.read_sql(query, engine)

    # Close the engine connection
    engine.dispose()

    return news_df


# Step 2: Analyze importance by normalizing reaction power with views
def analyze_news_importance(news_df):
    # Avoid dividing by zero views, so we handle that case
    news_df['views'] = news_df['views'].apply(lambda x: x if x > 0 else 1)

    # Create a new column for reaction power normalized by views
    # Normalizing the reaction power per view
    news_df.loc[:, 'reaction_power'] = (news_df['reactions_count'] + 2 * news_df['comments_count']) / news_df['views']

    # Sort by reaction power in descending order to get the most important news
    important_news_df = news_df.sort_values(by='reaction_power', ascending=False)
    return important_news_df


def filter_news(news_df):
    substrings = [
        "<STRING_TO_IGNORE>",
        "<STRING_TO_IGNORE>",
        "<STRING_TO_IGNORE>",
    ]

    condition = news_df['content'].str.contains('|'.join(substrings), na=False)

    # Negate the condition to filter out rows that contain any of the substrings
    filtered_df = news_df[~condition]

    return filtered_df


def shrink_content(s, max_length=1000):
    s = re.sub(r'#\S+', '', s)
    s = s.strip()[:max_length]
    return s


# Step 3: Present the most important highlights from the news
def input_for_scoring_with_gpt(news_df, max_length=1000):
    out = []
    for index, row in news_df.iterrows():
        out.append({
            'id': row['id'],
            'content': shrink_content(row['content'], max_length)
        })

    return out


def input_for_reporting_with_gpt(news_df):
    out = []
    for index, row in news_df.iterrows():
        out.append({
            'id': row['id'],
            'content': row['content'],
            'links': row['links'],
            'message_date': row['message_date'],
            'score': row['score']
        })

    return out

async def send_to_news_channel(message_text):
    try:
        await client.send_message(NEWS_CHANNEL_ID, message_text)
    except Exception as e:
        print(f"Error sending message to log channel: {str(e)}")

async def send_to_log_channel(message_text):
    try:
        await client.send_message(LOG_CHANNEL_ID, message_text)
    except Exception as e:
        print(f"Error sending message to log channel: {str(e)}")

# Function to log system messages both to console and Telegram channel
async def log_message(message_text):
    print(message_text)  # Print to console (system messages only)
    await send_to_log_channel(message_text)  # Send to Telegram log channel

# Example usage
if __name__ == "__main__":
    # Start the Telegram client with session string
    client.start()

    client.loop.run_until_complete(log_message("Querying the news from last 7 days"))

    # Step 1: Query the news from the last week
    news_df_raw = query_news_last_week(connection_string)

    news_df = filter_news(news_df_raw)

    # Step 2: Analyze news importance
    important_news_df = analyze_news_importance(news_df)

    log_msg = "Done fetching latest news, %d fetched" % len(important_news_df)
    client.loop.run_until_complete(log_message(log_msg))

    total_messages = len(news_df)
    # 120,000 символов было 46 тыщ токенов; 70 - должно быть типа 25,000 (лимит на 4o - 30k)
    golden_total_messages_length = 70000
    max_message_length = round(golden_total_messages_length / total_messages)

    gpt_input_scoring = input_for_scoring_with_gpt(news_df, max_message_length)

    scoring_prompt = '''
    Prompt: You are presented with the list of news messages, where reaction_power is the abstract 
    market reation score. Put the score from 0 to 1 (double digit precision) for every message in the 
    list, considering it's impact on retail market and Yandex Lavka business strategy. 
    Remember, that Yandex Lavka (RU: Яндекс Лавка) - one of the largest quick commerce 
    companies of Russia, which sells grocery and delivers them in 10-15 minutes across 8 
    largest cities in Russia, mainly Moscow and Saint-Petersburg.

    Score calibration: 

    - score of 0.0 should go to messages like: "Партнерская сеть ПВЗ «Ситилинка» выросла в пять 
    раз. Ситилинк. увеличил число ПВЗ до 6 тысяч. На сегодня география доставки охватывает 75 регионов России. 
    До конца 2024 года компания намерена увеличить количество партнерских ПВЗ еще на 15%, до 7 200 точек, 
    что вместе с собственными пунктами выдачи"

    - score of 1.0 should go to messages like: "Пострадавшие от ботулизма подали иски к «Самокату» и «Кухне на районе».
    В Дорогомиловский районный суд Москвы поступил первый иск к ООО «Умный ритейл» «о компенсации морального 
    вреда в связи с причинением вреда жизни и здоровью». Исковое заявление подано в связи с отравлением фасолью 
    в салате «Лобио»"

    Output format: json, 2 fields - id and score. Same length as input.

    Input:

    %{input}
    '''.format(input=gpt_input_scoring)

    client.loop.run_until_complete(log_message("Making a scoring request to ChatGPT"))
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai.api_key}"},

            json={
                "model": "gpt-4o-mini",
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": scoring_prompt}]
            }
        )

        # Print the answer
        scoring_response = json.loads(response.json()["choices"][0]["message"]["content"])["results"]
        log_msg = "Received scoring response, size %d" % len(scoring_response)
        client.loop.run_until_complete(log_message(log_msg))

    except Exception as e:
        print(response.json())
        print("An error occurred:", e)
        client.loop.run_until_complete(log_message(str(e)))

    news_scored_df = pd.DataFrame(scoring_response)

    important_news_scored_df = important_news_df\
        .merge(news_scored_df, on="id")

    important_news_scored_df["score"] += 5 * important_news_scored_df["reaction_power"]

    gpt_input_reporting = input_for_reporting_with_gpt(
        important_news_scored_df.sort_values(by="score", ascending=False).head(30))

    reporting_prompt = '''
    Prompt: You are presented with the prioritized list of news. Summarize the following news in the report
    with 10 highlights and for every highlight provide reasoning why every  news is important for 
    Yandex Lavka (RU: Яндекс Лавка) - one of the largest quick commerce companies of Russia, which sells 
    grocery and delivers them in 10-15 minutes across 8 largest cities in Russia, mainly Moscow and Saint-Petersburg.
    Merge the duplicate news. When summaring, try to preserve competitors names, names of people involved 
    and key metrics. Language: Write in russian. 

    Output format for every highlight: title, date, value for Yandex Lavka, link to source

    Input:

    %{input}
    '''.format(input=gpt_input_reporting)

    client.loop.run_until_complete(log_message("Crafting a report with ChatGPT"))
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai.api_key}"},

            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": reporting_prompt}]
            }
        )

        # Print the answer
        report_response = response.json()["choices"][0]["message"]["content"].strip()
        client.loop.run_until_complete(send_to_news_channel(report_response))
    except Exception as e:
        print(response.json())
        print("An error occurred:", e)
        client.loop.run_until_complete(log_message(str(e)))

