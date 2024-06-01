import decouple
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = decouple.config('TG_API_ID', cast=str)
api_hash = decouple.config('TG_API_HASH', cast=str)

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())