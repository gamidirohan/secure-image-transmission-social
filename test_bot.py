"""
Simple test script to check if the Telegram bot is working.
"""

import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_API_TOKEN')

async def test_bot():
    """Test if the bot is working."""
    try:
        # Create a client
        client = TelegramClient('test_session', API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
        
        # Get the bot info
        me = await client.get_me()
        print(f"Bot username: @{me.username}")
        print(f"Bot ID: {me.id}")
        print("Bot is working!")
        
        # Disconnect
        await client.disconnect()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Telegram bot...")
    import asyncio
    asyncio.run(test_bot())
