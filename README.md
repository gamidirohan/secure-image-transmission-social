# Telegram Image Bot

A Telegram bot that can send and receive images. This bot allows you to:
- Receive and save images sent by users
- Send saved images to specific chat IDs
- List all saved images

## Setup

1. Make sure you have Python installed (3.9+ recommended)
2. Create and activate a virtual environment:
   ```
   python -m venv myenv
   .\myenv\Scripts\activate  # Windows
   source myenv/bin/activate  # Linux/Mac
   ```
3. Install the required packages:
   ```
   pip install python-telegram-bot
   ```
4. Get a bot token from [@BotFather](https://t.me/botfather) on Telegram
5. Edit the `telegram_image_bot.py` or `telegram_image_bot_advanced.py` file and replace `YOUR_BOT_TOKEN_HERE` with your actual bot token
6. The default chat ID for testing is set to `1480128324`. You can change this in the code if needed.

## Basic Usage

Run the basic bot:
```
python telegram_image_bot.py
```

This will start the bot in polling mode, and it will respond to messages sent to it on Telegram.

## Advanced Usage

The advanced version supports command-line arguments for sending images:

### Run the bot normally:
```
python telegram_image_bot_advanced.py
```

### Send an image to a specific chat ID:
```
python telegram_image_bot_advanced.py --send --chat_id YOUR_CHAT_ID
```

### Send an image using the default chat ID:
```
python telegram_image_bot_advanced.py --send
```

### Send a specific image to a chat ID:
```
python telegram_image_bot_advanced.py --send --chat_id YOUR_CHAT_ID --image path/to/image.jpg
```

## Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/send_image [chat_id]` - Send an image to a specific chat ID
- `/list_images` - List all saved images (advanced version only)

## How to Get Chat IDs

1. Add the bot to a group or start a private chat with it
2. Send a message to the bot
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser
4. Look for the `"chat":{"id":` field in the response to find the chat ID

## Notes

- Images are saved in the `received_images` directory
- The bot will automatically create this directory if it doesn't exist
- When sending an image without specifying which one, the bot will send the most recently saved image
