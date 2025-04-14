#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script to download sample images for testing.
"""

import os
import logging
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Directory for sample images
SAMPLE_IMAGES_DIR = "sample_images"
os.makedirs(SAMPLE_IMAGES_DIR, exist_ok=True)

# Sample image URLs
SAMPLE_IMAGES = [
    {
        "url": "https://picsum.photos/800/600",
        "filename": "sample1.jpg"
    },
    {
        "url": "https://picsum.photos/600/800",
        "filename": "sample2.jpg"
    },
    {
        "url": "https://picsum.photos/1024/768",
        "filename": "sample3.jpg"
    }
]

def download_image(url, filename):
    """Download an image from a URL and save it to the sample images directory."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save the image
        image_path = os.path.join(SAMPLE_IMAGES_DIR, filename)
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded {url} to {image_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

def main():
    """Download sample images for testing."""
    logger.info("Downloading sample images...")

    success_count = 0
    for image in SAMPLE_IMAGES:
        if download_image(image["url"], image["filename"]):
            success_count += 1

    logger.info(f"Downloaded {success_count} of {len(SAMPLE_IMAGES)} images.")

if __name__ == '__main__':
    main()
