from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from sqlalchemy import create_engine, Column, String, Text, BigInteger, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from decouple import config
import json

# Read Telegram credentials stored as JSON in environment variable
telegram_credentials = json.loads(config('FOCUS_NEWS_TG_CREDS'))  # Updated

# Extract the individual credentials with lower case parameter names
api_id = telegram_credentials['api_id']
api_hash = telegram_credentials['api_hash']
session_string = telegram_credentials['session_string']

# Read PostgreSQL database URL from environment variable
DATABASE_URL = config('FOCUS_NEWS_DB')  # Updated

# Initialize Telegram Client with session string
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Channel to send log messages
LOG_CHANNEL_ID = <LOG_CHANNEL_ID>  # ID of the 'Фокус News Logs' channel

# Database setup using SQLAlchemy with PostgreSQL
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define a table to store the news messages, with BigInteger for large IDs
class News(Base):
    __tablename__ = 'news'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False)
    channel_title = Column(String, nullable=False)
    message_id = Column(BigInteger, nullable=False, unique=True)
    content = Column(Text, nullable=False)  # Formatted message text
    links = Column(Text, nullable=True)  # Store links as comma-separated URLs
    message_date = Column(DateTime, nullable=False)
    read_at = Column(DateTime, nullable=False)  # Time the message was first saved
    last_updated_at = Column(DateTime, nullable=False)  # Time the message was last updated
    views = Column(Integer)  # Number of views
    reactions_count = Column(Integer)  # Number of reactions (if any)
    comments_count = Column(Integer)  # Number of comments (replies)

# Define a table to track executions
class Execution(Base):
    __tablename__ = 'execution'
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_number = Column(Integer, nullable=False)
    execution_time = Column(DateTime, nullable=False)

# Create the tables if they don't exist
Base.metadata.create_all(engine)

# Session maker
Session = sessionmaker(bind=engine)
session = Session()

# News channel information in JSON structure; as many as you need
news_channel_info = [
    {"id": "<ID>", "title":  "<TITLE>", "link": "<LINK>"},
    {"id": "<ID>", "title": "<TITLE>", "link": "<LINK>"}
]

# Function to extract links from the message
def extract_links(entities, message_text):
    links = []
    if entities:  # Ensure entities is not None
        for entity in entities:
            if isinstance(entity, MessageEntityTextUrl):
                # If it's a text URL entity, extract the URL from the entity itself
                links.append(entity.url)
            elif isinstance(entity, MessageEntityUrl):
                # If it's a URL in the message text, extract the URL from the text
                url = message_text[entity.offset:entity.offset + entity.length]
                if url:
                    links.append(url)
    return links

# Function to get the current execution number and time
def get_next_execution():
    last_execution = session.query(Execution).order_by(Execution.execution_number.desc()).first()
    execution_number = last_execution.execution_number + 1 if last_execution else 1
    execution_time = datetime.utcnow()

    # Save this execution in the database
    new_execution = Execution(execution_number=execution_number, execution_time=execution_time)
    session.add(new_execution)
    session.commit()

    return execution_number, execution_time

# Function to send a message to the log channel
async def send_to_log_channel(message_text):
    try:
        await client.send_message(LOG_CHANNEL_ID, message_text)
    except Exception as e:
        print(f"Error sending message to log channel: {str(e)}")

# Function to log system messages both to console and Telegram channel
async def log_message(message_text):
    print(message_text)  # Print to console (system messages only)
    await send_to_log_channel(message_text)  # Send to Telegram log channel

# Fetch latest messages from a channel and update or insert them in the database
async def fetch_messages(channel_id, channel_title, execution_number, read_time, channel_link=None):
    try:
        # Use link if available, otherwise use channel_id
        entity = await client.get_entity(channel_link if channel_link else channel_id)

        # Get the latest 100 messages
        history = await client(GetHistoryRequest(
            peer=entity,
            limit=100,  # Always fetch the last 100 messages
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))

        # Check each message and insert or update it in the database
        for message in history.messages:
            if message.message:
                # Collect the number of views, reactions, and comments
                views = message.views if message.views is not None else 0
                reactions_count = sum(reaction.count for reaction in message.reactions.results) if message.reactions else 0
                comments_count = message.replies.replies if message.replies else 0

                # Extract links from the message
                links = extract_links(message.entities, message.raw_text)
                links_str = ','.join(links)  # Convert links to comma-separated string

                # Check if the message is already in the database
                existing_message = session.query(News).filter_by(message_id=message.id).first()

                if existing_message:
                    # Update the existing message
                    existing_message.content = message.message
                    existing_message.links = links_str
                    existing_message.views = views
                    existing_message.reactions_count = reactions_count
                    existing_message.comments_count = comments_count
                    existing_message.last_updated_at = read_time  # Update the last updated time
                else:
                    # Insert a new message into the database
                    news_entry = News(
                        channel_id=channel_id,
                        channel_title=channel_title,
                        message_id=message.id,
                        content=message.message,  # Save the formatted text
                        links=links_str,  # Save the links as a comma-separated string
                        message_date=message.date,
                        read_at=read_time,  # Use the same read time for all messages in this execution
                        last_updated_at=read_time,  # Set the same time as last updated
                        views=views,
                        reactions_count=reactions_count,
                        comments_count=comments_count
                    )
                    session.add(news_entry)

        # Commit the changes to the database
        session.commit()

    except Exception as e:
        error_message = f"Error fetching messages from {channel_title}: {str(e)}"
        await log_message(error_message)

# Main function to run the bot and fetch messages from multiple channels (Synchronous)
def main():
    # Get the execution number and read time for this run
    execution_number, read_time = get_next_execution()

    # Start the Telegram client with session string
    client.start()

    # Log system message: execution started
    log_msg = f"Fetching messages during execution {execution_number}."
    client.loop.run_until_complete(log_message(log_msg))

    # Fetch messages from each channel synchronously
    for channel in news_channel_info:
        channel_id = channel['id']
        channel_title = channel['title']
        channel_link = channel.get('link')  # Use the 'link' if available, otherwise None

        system_msg = f"Fetching messages from channel: {channel_title}"
        client.loop.run_until_complete(log_message(system_msg))

        # Run the asynchronous fetch_messages function synchronously
        client.loop.run_until_complete(fetch_messages(channel_id, channel_title, execution_number, read_time, channel_link))

    # Log system message: execution completed
    system_msg = f"Execution {execution_number} completed at {read_time}"
    client.loop.run_until_complete(log_message(system_msg))

# Execute the main function
if __name__ == "__main__":
    with client:
        main()
