# Secure Image Sharing Telegram Bot

A Telegram bot that enables secure image sharing using advanced encryption techniques and biometric authentication.

## Features

- User registration with fingerprint verification
- Secure image encryption using a hybrid approach:
  - AES encryption for the image data
  - RSA encryption for the AES key
  - Biometric-influenced chaotic scrambling
- Secure image decryption with fingerprint verification
- FastAPI backend for handling encryption/decryption operations

## Architecture

The system consists of two main components:

1. **Telegram Bot (Telethon)**: Handles user interactions, including registration, sending images, and decryption requests.
2. **FastAPI Backend**: Processes fingerprint images, performs encryption/decryption operations, and manages user data.

## Prerequisites

- Python 3.9 or higher
- A Telegram bot token (obtained from [@BotFather](https://t.me/botfather))
- Telegram API credentials (API ID and API Hash from [my.telegram.org](https://my.telegram.org))

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/gamidirohan/secure-image-transmission-social.git
   cd secure-image-transmission-social
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv myenv
   # On Windows
   myenv\Scripts\activate
   # On Linux/Mac
   source myenv/bin/activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on the `.env.example` template:
   ```
   cp .env.example .env
   ```

5. Edit the `.env` file and add your Telegram bot token:
   ```
   API_ID=your_api_id
   API_HASH=your_API_hash_id
   BOT_API_TOKEN=your_bot_token_here
   ```

## Usage

1. Activate the virtual environment:
   ```
   # On Windows
   myenv\Scripts\activate
   # On Linux/Mac
   source myenv/bin/activate
   ```

2. Start the FastAPI backend server:
   ```
   uvicorn secure_image_server:app --reload
   ```

3. In a separate terminal (with virtual environment activated), start the Telegram bot:
   ```
   python secure_image_bot.py
   ```

   Note: The bot will automatically delete any existing session files before starting.

4. Interact with the bot on Telegram:
   - Use `/register` to register with your fingerprint
   - Use `/send_image` to send an encrypted image to another user
   - Use `/decrypt` to decrypt an image sent to you

## Bot Commands

- `/start` - Start the bot and get a welcome message
- `/help` - Show help information
- `/register` - Register with your fingerprint
- `/send_image` - Send an encrypted image to another user
- `/decrypt` - Decrypt an image sent to you

## Security Considerations

- Fingerprint images and features are stored securely on the server
- RSA key pairs are generated for each user during registration
- AES keys are generated uniquely for each image transmission
- Biometric verification is required for decryption
- The IV (Initialization Vector) for AES encryption is securely stored and retrieved for decryption

## Technical Details

### Encryption Process

1. The recipient's fingerprint features (stored during registration) are used to derive a biometric key
2. A random AES key is generated for the image
3. The AES key is encrypted using the recipient's public RSA key
4. The image is scrambled using a chaotic map influenced by the recipient's biometric key
5. The scrambled image is encrypted using AES in CBC mode with a random IV
6. All necessary data (encrypted image, encrypted AES key, IV, permutation map, fingerprint information) is stored on the server

### Decryption Process

1. The recipient uploads their fingerprint image for verification
2. Features are extracted from the uploaded fingerprint and compared with the stored fingerprint information
3. If verification succeeds, the encrypted AES key is decrypted using the recipient's private RSA key
4. The encrypted image is decrypted using the recovered AES key and the stored IV
5. The decrypted image is unscrambled using the stored permutation map
6. The original image is returned to the recipient

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The encryption/decryption logic is based on the CS_project.py implementation
- Thanks to the Telethon and FastAPI teams for their excellent libraries
