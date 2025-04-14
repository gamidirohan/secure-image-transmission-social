# Telegram Image Client

A Telegram client that can send and receive images using the Telethon library.

## Setup

1. Make sure you have Python installed (3.7+ recommended)
2. Create and activate a virtual environment:
   ```
   python -m venv myenv
   .\myenv\Scripts\activate  # Windows
   source myenv/bin/activate  # Linux/Mac
   ```
3. Install the required packages:
   ```
   pip install telethon python-dotenv requests
   ```
4. The app credentials and chat ID are stored in the `.env` file:
   - API_ID: 22158010
   - API_HASH: 5c5e7bd6c453ee3aeaf4aa63109d536c
   - CHAT_ID: 1480128324
   - APP_TITLE: "img encryption app"
   - APP_SHORT_NAME: "imgApp"

## Download Sample Images

Before using the client, download some sample images:

```
python download_sample_images.py
```

This will download 3 sample images to the `sample_images` directory.

## Running the Client

### Start the client to receive images:

```
python telegram_image_client.py
```

The first time you run this, you'll need to log in with your phone number and the verification code sent to your Telegram account.

### Send an image from the command line:

```
python send_image.py
```

This will send the first sample image to the default chat ID specified in the `.env` file.

### Send an image to a specific chat ID:

```
python send_image.py --chat_id YOUR_CHAT_ID
```

### Send a specific image:

```
python send_image.py --image path/to/image.jpg
```

### Specify a phone number for authentication:

```
python send_image.py --phone YOUR_PHONE_NUMBER
```

Example with all parameters:
```
python send_image.py --chat_id 1480128324 --image sample_images/sample1.jpg --phone +1234567890
```

### Authentication Notes

- You need to provide your phone number with the country code (e.g., +1234567890)
- You'll receive a verification code on your Telegram account that you need to enter
- The session is saved, so you only need to authenticate once
- If you have two-factor authentication enabled, you'll also need to provide your password

## Features

- Send images to any chat ID
- Receive and save images sent to your account
- Automatically download sample images for testing
- Environment variables for secure credential storage

## Directory Structure

- `sample_images/`: Contains sample images for testing
- `received_images/`: Stores images received from other users
- `.env`: Contains API credentials and default chat ID
- `telegram_image_client.py`: Main client for sending and receiving images
- `send_image.py`: Command-line tool for sending images
- `download_sample_images.py`: Script to download sample images
- `CS_project.py`: Main project file (do not modify)

## Notes

- The client uses the Telethon library, which is a Python interface to the Telegram API
- Images are saved with a filename format of `{sender_id}_{message_id}.jpg`
- The client will automatically create the necessary directories if they don't exist
