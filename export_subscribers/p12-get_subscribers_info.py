import decouple

# взять параметры из https://my.telegram.org/apps
name = decouple.config('TG_APP_NAME', cast=str)
api_id = decouple.config('TG_API_ID', cast=str)
api_hash = decouple.config('TG_API_HASH', cast=str)

# получить session string, выполнив скрипт p11-save_session_string.py
session_string = decouple.config('TG_SESSION_STRING', cast=str)

# отправить произвольный пост из своего канала в бот @userinfobot, скопировать Id
channel_id = decouple.config('TG_CHANNEL_ID', cast=int)

import datetime

import sys

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import ResolveUsernameRequest

from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChannelParticipantsSearch

async def main():
	original_stdout = sys.stdout 

	import datetime
	suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H:%m%S")
	filter_text = sys.argv[1]

	with open('filename_subscribers_%s_%s.txt' % (filter_text, suffix), 'w') as f:
		sys.stdout = f

		async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
			entity = await client.get_entity(channel_id)
			
			# ---------------------------------------
			offset = 0
			limit = 201
			my_filter = ChannelParticipantsSearch(filter_text)
			all_participants = []
			while_condition = True
			# ---------------------------------------
			# channel = client(GetFullChannelRequest(id=channel_id))
			while while_condition:
				# print("offset: %d" % offset)
				participants = await client(GetParticipantsRequest(channel=entity, filter=my_filter, offset=offset, limit=limit+offset, hash=0))
				all_participants.extend(participants.users)
				offset += len(participants.users)

				print("len(participants.users): %d" % len(participants.users))
				print("limit + offset: %d" % (limit + offset))

				if len(participants.users) < limit:
					print("end while")
					while_condition = False
				else:
					print("continue")
					pass

			for p in all_participants:
				print(p)

			# user_list = client.iter_participants(entity=entity)
			# async for _user in user_list:
			# 	print(_user)

		sys.stdout = original_stdout

async def run() -> asyncio.coroutine:
    await main()

asyncio.run(run())