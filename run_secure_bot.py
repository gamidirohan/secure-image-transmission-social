"""
Helper script to run both the FastAPI server and Telegram bot.
"""

import os
import sys
import subprocess
import time
import signal
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_env_file():
    """Check if .env file exists and has the required variables."""
    if not os.path.exists('.env'):
        logger.error("Error: .env file not found. Please create one based on .env.example.")
        return False
    
    with open('.env', 'r') as f:
        env_content = f.read()
    
    required_vars = ['API_ID', 'API_HASH', 'BOT_API_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if var not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def run_server_and_bot():
    """Run both the FastAPI server and Telegram bot."""
    if not check_env_file():
        return
    
    try:
        # Start the FastAPI server
        logger.info("Starting FastAPI server...")
        server_process = subprocess.Popen(
            [sys.executable, 'secure_image_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the server to start
        logger.info("Waiting for server to start...")
        time.sleep(5)
        
        # Check if server is still running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            logger.error(f"Server failed to start:\nStdout: {stdout}\nStderr: {stderr}")
            return
        
        logger.info("Server started successfully.")
        
        # Start the Telegram bot
        logger.info("Starting Telegram bot...")
        bot_process = subprocess.Popen(
            [sys.executable, 'secure_image_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("Bot started successfully.")
        logger.info("Press Ctrl+C to stop both processes.")
        
        # Wait for user to press Ctrl+C
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                logger.error(f"Server stopped unexpectedly:\nStdout: {stdout}\nStderr: {stderr}")
                break
            
            if bot_process.poll() is not None:
                stdout, stderr = bot_process.communicate()
                logger.error(f"Bot stopped unexpectedly:\nStdout: {stdout}\nStderr: {stderr}")
                break
    
    except KeyboardInterrupt:
        logger.info("Stopping processes...")
    
    finally:
        # Stop the processes
        if 'server_process' in locals() and server_process.poll() is None:
            logger.info("Stopping server...")
            server_process.terminate()
            server_process.wait(timeout=5)
        
        if 'bot_process' in locals() and bot_process.poll() is None:
            logger.info("Stopping bot...")
            bot_process.terminate()
            bot_process.wait(timeout=5)
        
        logger.info("All processes stopped.")

if __name__ == "__main__":
    run_server_and_bot()
