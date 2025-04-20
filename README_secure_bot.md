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
   git clone https://github.com/yourusername/secure-image-bot.git
   cd secure-image-bot
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
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
   API_ID=22158010
   API_HASH=5c5e7bd6c453ee3aeaf4aa63109d536c
   BOT_API_TOKEN=your_bot_token_here
   ```

## Usage

1. Start the FastAPI backend server:
   ```
   python secure_image_server.py
   ```

2. In a separate terminal, start the Telegram bot:
   ```
   python secure_image_bot.py
   ```

3. Interact with the bot on Telegram:
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

1. The sender's fingerprint features are extracted and used to derive a biometric key
2. A random AES key is generated for the image
3. The AES key is encrypted using the recipient's public RSA key
4. The image is scrambled using a chaotic map influenced by the sender's biometric key
5. The scrambled image is encrypted using AES in CBC mode with a random IV
6. All necessary data (encrypted image, encrypted AES key, IV, permutation map, minutiae count) is stored on the server

### Decryption Process

1. The recipient's fingerprint features are extracted and verified against the stored minutiae count
2. The encrypted AES key is decrypted using the recipient's private RSA key
3. The encrypted image is decrypted using the recovered AES key and the stored IV
4. The decrypted image is unscrambled using the stored permutation map
5. The original image is returned to the recipient

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The encryption/decryption logic is based on the CS_project.py implementation
- Thanks to the Telethon and FastAPI teams for their excellent libraries
