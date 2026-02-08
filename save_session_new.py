import decouple
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import sys

api_id = decouple.config('TG_API_ID', cast=int)
api_hash = decouple.config('TG_API_HASH', cast=str)

print("=" * 60)
print("Telegram Debug Mode")
print("=" * 60)
print(f"API ID: {api_id}")
print(f"API Hash: {api_hash[:10]}...{api_hash[-10:]}")
print()

try:
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("\n✅ Connected successfully!")
        
        if not client.is_user_authorized():
            print("\n⚠️  Need to authorize...")
            phone = input("Enter phone (with + and country code): ")
            print(f"📱 Sending code to: {phone}")
            
            client.send_code_request(phone)
            
            print("\n" + "=" * 60)
            print("CODE SENT!")
            print("=" * 60)
            print("Check these places in Telegram:")
            print("1. Service Notifications (official Telegram)")
            print("2. Your Saved Messages")
            print("3. All your Telegram apps (phone, desktop, web)")
            print("=" * 60)
            
            code = input("\nEnter the code you received: ")
            client.sign_in(phone, code)
        
        print("\n✅ Success! Your SESSION_STRING:\n")
        print(client.session.save())
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
    sys.exit(1)