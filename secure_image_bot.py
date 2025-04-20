"""
Telegram bot for secure image sharing using Telethon.
This bot handles user registration, sending encrypted images, and decryption.
"""

import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from dotenv import load_dotenv
import aiohttp
from aiohttp import FormData
import tempfile
from telethon.tl.types import InputMediaUploadedPhoto

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_API_TOKEN')

# FastAPI server URL
API_BASE_URL = "http://localhost:8000"

# User states for conversation handling
user_states = {}
user_data = {}

# Initialize the Telegram client
bot = TelegramClient('secure_image_bot', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handle the /start command."""
    await event.respond(
        "Welcome to the Secure Image Sharing Bot!\n\n"
        "This bot allows you to securely share images with other users using "
        "advanced encryption and biometric verification.\n\n"
        "Available commands:\n"
        "/register - Register with your fingerprint\n"
        "/send_image - Send an encrypted image to another user\n"
        "/decrypt - Decrypt an image sent to you\n"
        "/help - Show this help message"
    )
    return

@bot.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    """Handle the /help command."""
    await event.respond(
        "Secure Image Sharing Bot - Help\n\n"
        "Available commands:\n"
        "/register - Register with your fingerprint\n"
        "/send_image - Send an encrypted image to another user\n"
        "/decrypt - Decrypt an image sent to you\n"
        "/help - Show this help message\n\n"
        "How it works:\n"
        "1. Register by uploading your fingerprint image\n"
        "2. To send an image, specify the recipient's Telegram ID and upload the image\n"
        "3. To decrypt an image, use the message ID and upload your fingerprint for verification"
    )
    return

@bot.on(events.NewMessage(pattern='/register'))
async def register_handler(event):
    """Handle the /register command."""
    user_id = event.sender_id
    user_states[user_id] = 'awaiting_fingerprint_for_registration'

    await event.respond(
        "Please upload your fingerprint image for registration.\n"
        "The image should be clear and high-quality for better security."
    )
    return

@bot.on(events.NewMessage(pattern='/send_image'))
async def send_image_handler(event):
    """Handle the /send_image command."""
    user_id = event.sender_id

    # Check if user is registered
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/check_user/{user_id}") as response:
            if response.status != 200:
                await event.respond("You need to register first. Use /register command.")
                return

    user_states[user_id] = 'awaiting_recipient_id'
    user_data[user_id] = {}

    await event.respond(
        "Please enter the Telegram ID of the recipient.\n"
        "The recipient must be registered with this bot."
    )
    return

@bot.on(events.NewMessage(pattern='/decrypt'))
async def decrypt_handler(event):
    """Handle the /decrypt command."""
    user_id = event.sender_id

    # Check if user is registered
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/check_user/{user_id}") as response:
            if response.status != 200:
                await event.respond("You need to register first. Use /register command.")
                return

    # Check if user has any pending images
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/pending_images/{user_id}") as response:
            if response.status != 200:
                await event.respond("You don't have any pending encrypted images.")
                return

            pending_images = await response.json()

    if not pending_images:
        await event.respond("You don't have any pending encrypted images.")
        return

    # Create buttons for each pending image
    buttons = []
    for image in pending_images:
        sender_name = image.get('sender_name', 'Unknown')
        message_id = image.get('message_id')
        buttons.append([Button.inline(f"Image from {sender_name}", data=f"decrypt_{message_id}")])

    await event.respond("Select an image to decrypt:", buttons=buttons)
    return

@bot.on(events.CallbackQuery())
async def callback_handler(event):
    """Handle button callbacks."""
    user_id = event.sender_id
    data = event.data.decode('utf-8')

    if data.startswith('decrypt_'):
        message_id = data.split('_')[1]
        user_states[user_id] = 'awaiting_fingerprint_for_decryption'
        user_data[user_id] = {'message_id': message_id}

        await event.respond(
            "Please upload your fingerprint image for verification and decryption."
        )

    await event.answer()
    return

@bot.on(events.NewMessage())
async def message_handler(event):
    """Handle text messages based on user state."""
    user_id = event.sender_id

    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state == 'awaiting_recipient_id':
        try:
            recipient_id = int(event.text.strip())

            # Check if recipient is registered
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/check_user/{recipient_id}") as response:
                    if response.status != 200:
                        await event.respond("The recipient is not registered with this bot.")
                        return

            user_data[user_id]['recipient_id'] = recipient_id
            user_states[user_id] = 'awaiting_image_to_encrypt'

            await event.respond(
                f"Recipient ID {recipient_id} is valid.\n"
                "Now, please upload the image you want to encrypt and send."
            )
        except ValueError:
            await event.respond("Invalid Telegram ID. Please enter a valid numeric ID.")

    return

@bot.on(events.NewMessage(func=lambda e: e.photo))
async def photo_handler(event):
    """Handle photo uploads based on user state."""
    user_id = event.sender_id

    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state == 'awaiting_fingerprint_for_registration':
        # Download the fingerprint image
        photo = event.photo
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            fingerprint_path = temp_file.name

        await event.download_media(file=fingerprint_path)

        # Send the fingerprint to the server for registration
        async with aiohttp.ClientSession() as session:
            # Create form data with file
            form = FormData()
            form.add_field('user_id', str(user_id))
            form.add_field('fingerprint',
                          open(fingerprint_path, 'rb'),
                          filename='fingerprint.jpg',
                          content_type='image/jpeg')

            async with session.post(
                f"{API_BASE_URL}/register",
                data=form
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    await event.respond(
                        "Registration successful!\n"
                        f"Your fingerprint has been processed and stored securely.\n"
                        f"Number of minutiae detected: {result.get('num_minutiae', 'N/A')}\n\n"
                        "You can now use /send_image to send encrypted images to other users."
                    )
                else:
                    error_msg = await response.text()
                    await event.respond(f"Registration failed: {error_msg}")

        # Clean up
        os.unlink(fingerprint_path)
        user_states.pop(user_id, None)

    elif state == 'awaiting_image_to_encrypt':
        # Download the image to encrypt
        photo = event.photo
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            image_path = temp_file.name

        await event.download_media(file=image_path)

        recipient_id = user_data[user_id]['recipient_id']

        # Send the image to the server for encryption
        async with aiohttp.ClientSession() as session:
            # Create form data with file
            form = FormData()
            form.add_field('sender_id', str(user_id))
            form.add_field('recipient_id', str(recipient_id))
            form.add_field('image',
                          open(image_path, 'rb'),
                          filename='image.jpg',
                          content_type='image/jpeg')

            await event.respond("Encrypting your image... This may take a moment.")

            async with session.post(
                f"{API_BASE_URL}/encrypt",
                data=form
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    message_id = result.get('message_id')

                    # Notify the recipient
                    try:
                        await bot.send_message(
                            recipient_id,
                            f"You have received an encrypted image from user {user_id}.\n"
                            f"Message ID: {message_id}\n"
                            "Use /decrypt to view and decrypt this image."
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify recipient: {e}")

                    await event.respond(
                        "Image encrypted and sent successfully!\n"
                        f"Message ID: {message_id}\n"
                        "The recipient has been notified."
                    )
                else:
                    error_msg = await response.text()
                    await event.respond(f"Encryption failed: {error_msg}")

        # Clean up
        os.unlink(image_path)
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)

    elif state == 'awaiting_fingerprint_for_decryption':
        # Download the fingerprint image
        photo = event.photo
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            fingerprint_path = temp_file.name

        await event.download_media(file=fingerprint_path)

        message_id = user_data[user_id]['message_id']

        # Send the fingerprint to the server for decryption
        async with aiohttp.ClientSession() as session:
            # Create form data with file
            form = FormData()
            form.add_field('user_id', str(user_id))
            form.add_field('message_id', message_id)
            form.add_field('fingerprint',
                          open(fingerprint_path, 'rb'),
                          filename='fingerprint.jpg',
                          content_type='image/jpeg')

            await event.respond("Verifying your fingerprint and decrypting the image... This may take a moment.")

            async with session.post(
                f"{API_BASE_URL}/decrypt",
                data=form
            ) as response:
                if response.status == 200:
                    # Save the decrypted image
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        decrypted_path = temp_file.name

                    with open(decrypted_path, 'wb') as f:
                        f.write(await response.read())

                    # Send the decrypted image back to the user
                    await bot.send_file(
                        user_id,
                        decrypted_path,
                        caption="Here is your decrypted image!"
                    )

                    # Clean up
                    os.unlink(decrypted_path)
                else:
                    error_msg = await response.text()
                    await event.respond(f"Decryption failed: {error_msg}")

        # Clean up
        os.unlink(fingerprint_path)
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)

    return

async def main():
    """Start the bot."""
    await bot.start(bot_token=BOT_TOKEN)

    # Check if the API server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    logger.info("Connected to FastAPI server successfully")
                else:
                    logger.warning("FastAPI server is running but returned an error")
    except:
        logger.error("Could not connect to FastAPI server. Make sure it's running.")

    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
