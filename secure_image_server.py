"""
FastAPI server for secure image sharing.
This server handles user registration, image encryption, and decryption.
"""

import os
import uuid
import shutil
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import cv2
import numpy as np
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import json
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from skimage.morphology import skeletonize

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create directories for storage
os.makedirs("data/users", exist_ok=True)
os.makedirs("data/images", exist_ok=True)
os.makedirs("data/keys", exist_ok=True)

app = FastAPI(title="Secure Image Sharing API")


# File to store per-message metrics and events (JSON lines)
STATS_FILE = "data/message_stats.jsonl"
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

def append_stats(record: dict):
    """Append a JSON record to the stats file (one JSON object per line)."""
    try:
        with open(STATS_FILE, "a", encoding="utf-8") as sf:
            json.dump(record, sf)
            sf.write("\n")
    except Exception as e:
        logger.error(f"Failed to append stats record: {e}")

# A single combined file that stores full records (metadata + metrics) for each message
ALL_RECORDS_FILE = "data/all_records.jsonl"
os.makedirs(os.path.dirname(ALL_RECORDS_FILE), exist_ok=True)

def append_all(record: dict):
    """Append a JSON record to the combined all_records file (one JSON object per line)."""
    try:
        with open(ALL_RECORDS_FILE, "a", encoding="utf-8") as sf:
            json.dump(record, sf)
            sf.write("\n")
    except Exception as e:
        logger.error(f"Failed to append to all records file: {e}")

# In-memory database for simplicity (replace with a real database in production)
users_db = {}  # user_id -> user_data
images_db = {}  # message_id -> image_data

# Models
class User(BaseModel):
    user_id: str
    num_minutiae: int
    registration_date: datetime
    fingerprint_path: str
    public_key_path: str
    private_key_path: str

class ImageMessage(BaseModel):
    message_id: str
    sender_id: str
    recipient_id: str
    timestamp: datetime
    encrypted_image_path: str
    encrypted_aes_key_path: str
    iv_path: str
    permutation_path: str
    minutiae_count: int
    fingerprint_info_path: str

# Helper functions from CS_project.py
def generate_aes_key():
    """Generate a random AES key."""
    return os.urandom(32)  # 256-bit AES key

def generate_rsa_key_pair():
    """Generate an RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def encrypt_aes_key(aes_key, public_key):
    """Encrypt the AES key using RSA."""
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted_key

def decrypt_aes_key(encrypted_key, private_key):
    """Decrypt the AES key using RSA."""
    decrypted_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted_key

def detect_minutiae_cn(thinned_image):
    """Detect minutiae using the Crossing Number method."""
    # Convert to a signed integer type to prevent overflow in abs() calculations
    thinned_image = thinned_image.astype(np.int16)

    minutiae = []
    height, width = thinned_image.shape

    for i in range(1, height - 1):
        for j in range(1, width - 1):
            if thinned_image[i, j] == 255:  # Only consider ridge pixels (255 is white)
                neighborhood = [
                    thinned_image[i - 1, j - 1] // 255,
                    thinned_image[i - 1, j] // 255,
                    thinned_image[i - 1, j + 1] // 255,
                    thinned_image[i, j + 1] // 255,
                    thinned_image[i + 1, j + 1] // 255,
                    thinned_image[i + 1, j] // 255,
                    thinned_image[i + 1, j - 1] // 255,
                    thinned_image[i, j - 1] // 255
                ]

                cn = 0
                for k in range(8):
                    cn += abs(neighborhood[k] - neighborhood[(k + 1) % 8])

                cn //= 2

                if cn == 1:
                    minutiae.append(('ending', j, i))
                elif cn == 3:
                    minutiae.append(('bifurcation', j, i))

    return minutiae

def extract_fingerprint_features_cn(fingerprint_path):
    """Extract fingerprint features using the Crossing Number method."""
    try:
        logger.info(f"Processing fingerprint image: {fingerprint_path}")
        img = cv2.imread(fingerprint_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            logger.error(f"Could not load fingerprint image: {fingerprint_path}")
            return None

        logger.info(f"Fingerprint image loaded successfully. Shape: {img.shape}")

        # 1. Preprocessing
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        equalized = cv2.equalizeHist(blurred)
        logger.info("Preprocessing completed")

        # 2. Segmentation and Binarization
        _, binary_img = cv2.threshold(equalized, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        logger.info(f"Binarization completed. Binary image shape: {binary_img.shape}")

        # Save intermediate images for debugging
        debug_dir = os.path.dirname(fingerprint_path)
        cv2.imwrite(f"{debug_dir}/binary.jpg", binary_img)

        # 3. Ridge Thinning (using skeletonize from skimage)
        thinned = skeletonize(binary_img // 255).astype(np.uint8) * 255
        logger.info(f"Thinning completed. Thinned image shape: {thinned.shape}")
        cv2.imwrite(f"{debug_dir}/thinned.jpg", thinned)

        # 4. Minutiae Detection using Crossing Number
        minutiae = detect_minutiae_cn(thinned)
        logger.info(f"Minutiae detection completed. Found {len(minutiae)} minutiae")

        return minutiae

    except Exception as e:
        logger.error(f"Fingerprint feature extraction failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def logistic_map_scramble_biometric(image, biometric_key, num_minutiae):
    """Scramble the image using a logistic map with biometric influence."""
    height, width, channels = image.shape
    total_pixels = height * width * channels  # Total number of pixels

    # Generate chaotic sequence with length equal to the number of minutiae
    chaotic_sequence = np.zeros(num_minutiae)
    x = biometric_key
    r = 3.99

    for i in range(num_minutiae):
        x = r * x * (1 - x)
        chaotic_sequence[i] = x

    # Create a permutation of pixel indices based on the chaotic sequence
    rng = np.random.RandomState(int(np.sum(chaotic_sequence) * 100000) % (2**32 - 1) if num_minutiae > 0 else 0)
    permutation = rng.permutation(total_pixels)

    # Scramble the image
    flattened_image = image.flatten()
    scrambled_flattened = flattened_image[permutation]
    scrambled_image = scrambled_flattened.reshape(image.shape)

    return scrambled_image, permutation

def reverse_logistic_map_biometric(scrambled_image, permutation, original_shape):
    """Reverse the chaotic scrambling."""
    flattened_scrambled = scrambled_image.flatten()
    original_flattened = np.zeros_like(flattened_scrambled)
    inverse_permutation = np.argsort(permutation)
    original_flattened = flattened_scrambled[inverse_permutation]
    original_image = original_flattened.reshape(original_shape)
    return original_image

def aes_encrypt_image(image, key):
    """Encrypt an image using AES in CBC mode (operates on raw pixel bytes to avoid lossy compression)."""
    # Generate a random IV
    iv = os.urandom(16)

    # Convert image to raw bytes (flattened) and pad to AES block size
    height, width, channels = image.shape
    flat = image.flatten()
    # Compute padded size (multiple of 16)
    padded_size = (flat.size + 16) // 16 * 16
    padded = np.pad(flat, (0, padded_size - flat.size), mode='constant')

    # Encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_img = encryptor.update(padded.tobytes()) + encryptor.finalize()

    return iv, encrypted_img

def aes_decrypt_image(encrypted_img, key, iv, original_shape):
    """Decrypt an image using AES in CBC mode and reconstruct raw pixel array."""
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    decrypted_padded = decryptor.update(encrypted_img) + decryptor.finalize()

    # Convert back to numpy array and reshape to original shape
    height, width, channels = original_shape
    total = height * width * channels
    arr = np.frombuffer(decrypted_padded, dtype=np.uint8)[:total]
    try:
        decrypted_image = arr.reshape(original_shape)
    except Exception:
        # If reshape fails, try to convert to uint8 and reshape
        decrypted_image = np.copy(arr[:total]).astype(np.uint8).reshape((height, width, channels))

    return decrypted_image

def derive_biometric_key(minutiae):
    """Derive a biometric key from fingerprint minutiae."""
    if not minutiae:
        return 0.5, 0  # Default values if no minutiae found

    # Extract coordinates
    coordinates = [(x, y) for type, x, y in minutiae]

    # Calculate biometric key as in CS_project.py
    biometric_key_raw = np.mean([sum(coord) for coord in coordinates]) / (len(minutiae) + 1e-9) if coordinates else 0.7

    # Normalize the biometric key to be within (0, 1)
    biometric_key = biometric_key_raw % 1.0  # Taking the fractional part

    # Avoid extreme values that lead to non-chaotic behavior
    if biometric_key < 0.1:
        biometric_key = 0.1  # Avoid key being exactly 0
    elif biometric_key > 0.9:
        biometric_key = 0.9

    return biometric_key, biometric_key_raw

# API endpoints
@app.get("/health")
async def health_check():
    """Check if the server is running."""
    return {"status": "ok"}

@app.get("/check_user/{user_id}")
async def check_user(user_id: str):
    """Check if a user is registered."""
    if user_id in users_db:
        return {"registered": True}
    else:
        raise HTTPException(status_code=404, detail="User not registered")

@app.post("/register")
async def register_user(
    user_id: str = Form(...),
    fingerprint: UploadFile = File(...)
):
    """Register a new user with their fingerprint."""
    # Save the fingerprint image
    fingerprint_dir = f"data/users/{user_id}"
    os.makedirs(fingerprint_dir, exist_ok=True)

    fingerprint_path = f"{fingerprint_dir}/fingerprint.jpg"
    with open(fingerprint_path, "wb") as f:
        f.write(await fingerprint.read())

    # Extract fingerprint features
    minutiae = extract_fingerprint_features_cn(fingerprint_path)
    if not minutiae:
        raise HTTPException(status_code=400, detail="Could not extract fingerprint features")

    num_minutiae = len(minutiae)

    # Generate RSA key pair
    private_key, public_key = generate_rsa_key_pair()

    # Save keys
    keys_dir = f"data/keys/{user_id}"
    os.makedirs(keys_dir, exist_ok=True)

    # Save private key in PEM format
    private_key_path = f"{keys_dir}/private_key.pem"
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save public key in PEM format
    public_key_path = f"{keys_dir}/public_key.pem"
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    # Store user data
    user = User(
        user_id=user_id,
        num_minutiae=num_minutiae,
        registration_date=datetime.now(),
        fingerprint_path=fingerprint_path,
        public_key_path=public_key_path,
        private_key_path=private_key_path
    )

    users_db[user_id] = user

    return {"status": "success", "num_minutiae": num_minutiae}

@app.post("/encrypt")
async def encrypt_image(
    sender_id: str = Form(...),
    recipient_id: str = Form(...),
    image: UploadFile = File(...)
):
    """Encrypt an image for a recipient."""
    # Check if both users are registered
    if sender_id not in users_db:
        raise HTTPException(status_code=404, detail="Sender not registered")
    if recipient_id not in users_db:
        raise HTTPException(status_code=404, detail="Recipient not registered")

    # Start timer for encryption operation
    encrypt_start = time.perf_counter()

    # Save the original image
    message_id = str(uuid.uuid4())
    message_dir = f"data/images/{message_id}"
    os.makedirs(message_dir, exist_ok=True)

    original_image_path = f"{message_dir}/original.jpg"
    with open(original_image_path, "wb") as f:
        f.write(await image.read())

    # Log original image size
    try:
        original_size = os.path.getsize(original_image_path)
    except Exception:
        original_size = None
    logger.info(f"[encrypt] message_id={message_id} original_size={original_size} bytes")

    # Load the image
    original_image = cv2.imread(original_image_path)
    if original_image is None:
        raise HTTPException(status_code=400, detail="Could not load image")

    # Get recipient's fingerprint features (for biometric-based scrambling)
    recipient = users_db[recipient_id]
    minutiae = extract_fingerprint_features_cn(recipient.fingerprint_path)
    if not minutiae:
        raise HTTPException(status_code=400, detail="Could not extract recipient's fingerprint features")

    num_minutiae = len(minutiae)

    # Derive biometric key from recipient's fingerprint
    biometric_key, biometric_key_raw = derive_biometric_key(minutiae)
    logger.info(f"Using recipient's fingerprint for encryption. Minutiae count: {num_minutiae}")
    logger.info(f"Derived biometric key: {biometric_key}")

    # Store the recipient's fingerprint information for verification during decryption
    recipient_fingerprint_info = {
        "num_minutiae": num_minutiae,
        "biometric_key": biometric_key
    }

    # Generate AES key
    aes_key = generate_aes_key()

    # Load recipient's public key
    recipient = users_db[recipient_id]
    with open(recipient.public_key_path, "rb") as f:
        recipient_public_key = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

    # Encrypt AES key using recipient's public key
    encrypted_aes_key = encrypt_aes_key(aes_key, recipient_public_key)

    # Apply chaotic scrambling with Logistic Map, influenced by biometrics
    scramble_start = time.perf_counter()
    scrambled_image, permutation = logistic_map_scramble_biometric(
        original_image.copy(), biometric_key, num_minutiae
    )
    scramble_end = time.perf_counter()
    logger.info(f"[encrypt] message_id={message_id} scramble_time={scramble_end-scramble_start:.4f}s")

    # Save a visual preview (scrambled) so recipients can view the encrypted-looking image in-chat
    scrambled_preview_path = f"{message_dir}/scrambled_preview.jpg"
    try:
        # Convert and write scrambled image as JPEG preview
        cv2.imwrite(scrambled_preview_path, scrambled_image)
    except Exception as e:
        logger.warning(f"Failed to write scrambled preview image: {e}")

    # Apply AES Encryption
    aes_start = time.perf_counter()
    iv, encrypted_image = aes_encrypt_image(scrambled_image, aes_key)
    aes_end = time.perf_counter()
    logger.info(f"[encrypt] message_id={message_id} aes_encrypt_time={aes_end-aes_start:.4f}s")

    # Save encrypted data
    encrypted_image_path = f"{message_dir}/encrypted_image.bin"
    with open(encrypted_image_path, "wb") as f:
        f.write(encrypted_image)

    # Log encrypted image size
    try:
        encrypted_size = os.path.getsize(encrypted_image_path)
    except Exception:
        encrypted_size = len(encrypted_image) if encrypted_image is not None else None
    logger.info(f"[encrypt] message_id={message_id} encrypted_size={encrypted_size} bytes")

    encrypted_aes_key_path = f"{message_dir}/encrypted_aes_key.bin"
    with open(encrypted_aes_key_path, "wb") as f:
        f.write(encrypted_aes_key)

    iv_path = f"{message_dir}/iv.bin"
    with open(iv_path, "wb") as f:
        f.write(iv)

    permutation_path = f"{message_dir}/permutation.npy"
    np.save(permutation_path, permutation)

    minutiae_count_path = f"{message_dir}/minutiae_count.txt"
    with open(minutiae_count_path, "w") as f:
        f.write(str(num_minutiae))

    # Save recipient's fingerprint info for verification
    fingerprint_info_path = f"{message_dir}/fingerprint_info.json"
    with open(fingerprint_info_path, "w") as f:
        json.dump(recipient_fingerprint_info, f)

    # Store image message data
    image_message = ImageMessage(
        message_id=message_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        timestamp=datetime.now(),
        encrypted_image_path=encrypted_image_path,
        encrypted_aes_key_path=encrypted_aes_key_path,
        iv_path=iv_path,
        permutation_path=permutation_path,
        minutiae_count=num_minutiae,
        fingerprint_info_path=fingerprint_info_path
    )

    images_db[message_id] = image_message

    encrypt_end = time.perf_counter()
    logger.info(f"[encrypt] message_id={message_id} total_encrypt_time={encrypt_end-encrypt_start:.4f}s")

    # Persist metrics for this encryption event
    try:
        encrypt_record = {
            "event": "encrypt",
            "message_id": message_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "timestamp": datetime.utcnow().isoformat(),
            "original_size": original_size,
            "encrypted_size": encrypted_size,
            "scramble_time_s": round(scramble_end - scramble_start, 6),
            "aes_encrypt_time_s": round(aes_end - aes_start, 6),
            "total_encrypt_time_s": round(encrypt_end - encrypt_start, 6)
        }
        append_stats(encrypt_record)
        # Also append a full combined record with metadata and file paths
        try:
            full_record = {
                "event": "encrypt_full",
                "message_id": message_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "original_path": original_image_path,
                "preview_path": scrambled_preview_path,
                "encrypted_path": encrypted_image_path,
                "encrypted_aes_key_path": encrypted_aes_key_path,
                "iv_path": iv_path,
                "permutation_path": permutation_path,
                "minutiae_count_path": minutiae_count_path,
                "fingerprint_info_path": fingerprint_info_path,
                "original_size": original_size,
                "encrypted_size": encrypted_size,
                "scramble_time_s": round(scramble_end - scramble_start, 6),
                "aes_encrypt_time_s": round(aes_end - aes_start, 6),
                "total_encrypt_time_s": round(encrypt_end - encrypt_start, 6)
            }
            append_all(full_record)
        except Exception as e:
            logger.error(f"Failed to append full encrypt record: {e}")
    except Exception as e:
        logger.error(f"Failed to record encrypt metrics: {e}")

    return {"status": "success", "message_id": message_id}


@app.get("/preview/{message_id}")
async def download_preview_image(message_id: str):
    """Return the scrambled preview image (JPEG) for a given message id."""
    if message_id not in images_db:
        raise HTTPException(status_code=404, detail="Message not found")

    image_message = images_db[message_id]
    # preview is stored next to encrypted image
    preview_path = os.path.join(os.path.dirname(image_message.encrypted_image_path), "scrambled_preview.jpg")
    if not os.path.exists(preview_path):
        raise HTTPException(status_code=404, detail="Preview image not found")

    return FileResponse(preview_path, media_type="image/jpeg", filename="scrambled_preview.jpg")

@app.get("/download_encrypted/{message_id}")
async def download_encrypted_image(message_id: str):
    """Return the encrypted image file for a given message id."""
    if message_id not in images_db:
        raise HTTPException(status_code=404, detail="Message not found")

    image_message = images_db[message_id]
    encrypted_path = image_message.encrypted_image_path
    if not os.path.exists(encrypted_path):
        raise HTTPException(status_code=404, detail="Encrypted image file not found")

    # Serve the encrypted binary file
    return FileResponse(encrypted_path, media_type="application/octet-stream", filename="encrypted_image.bin")

@app.get("/pending_images/{user_id}")
async def get_pending_images(user_id: str):
    """Get a list of pending encrypted images for a user."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not registered")

    pending_images = []
    for message_id, image_message in images_db.items():
        if image_message.recipient_id == user_id:
            pending_images.append({
                "message_id": message_id,
                "sender_id": image_message.sender_id,
                "sender_name": f"User {image_message.sender_id}",
                "timestamp": image_message.timestamp.isoformat()
            })

    return pending_images

@app.post("/decrypt")
async def decrypt_image(
    user_id: str = Form(...),
    message_id: str = Form(...),
    fingerprint: UploadFile = File(...)
):
    """Decrypt an image using the recipient's fingerprint."""
    # Check if user is registered
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not registered")

    # Check if message exists
    if message_id not in images_db:
        raise HTTPException(status_code=404, detail="Message not found")

    image_message = images_db[message_id]

    # Check if user is the intended recipient
    if image_message.recipient_id != user_id:
        raise HTTPException(status_code=403, detail="You are not the intended recipient of this message")

    # Save the fingerprint image
    temp_fingerprint_path = f"data/temp_{message_id}_fingerprint.jpg"
    with open(temp_fingerprint_path, "wb") as f:
        f.write(await fingerprint.read())

    # Extract fingerprint features from the uploaded fingerprint
    minutiae = extract_fingerprint_features_cn(temp_fingerprint_path)
    if not minutiae:
        os.remove(temp_fingerprint_path)
        raise HTTPException(status_code=400, detail="Could not extract fingerprint features")

    num_minutiae = len(minutiae)

    # Load the stored fingerprint information
    with open(image_message.fingerprint_info_path, "r") as f:
        stored_fingerprint_info = json.load(f)

    # Derive biometric key from the uploaded fingerprint
    biometric_key, _ = derive_biometric_key(minutiae)

    # Check if the fingerprint matches (with some tolerance)
    minutiae_match = abs(num_minutiae - stored_fingerprint_info["num_minutiae"]) <= 5
    key_match = abs(biometric_key - stored_fingerprint_info["biometric_key"]) < 0.1

    logger.info(f"Fingerprint verification: Uploaded minutiae: {num_minutiae}, Stored minutiae: {stored_fingerprint_info['num_minutiae']}")
    logger.info(f"Fingerprint verification: Uploaded key: {biometric_key}, Stored key: {stored_fingerprint_info['biometric_key']}")

    if not (minutiae_match and key_match):
        os.remove(temp_fingerprint_path)
        raise HTTPException(status_code=403, detail="Fingerprint verification failed")

    # Load recipient's private key
    user = users_db[user_id]
    with open(user.private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    # Load encrypted data
    with open(image_message.encrypted_aes_key_path, "rb") as f:
        encrypted_aes_key = f.read()

    with open(image_message.encrypted_image_path, "rb") as f:
        encrypted_image = f.read()

    with open(image_message.iv_path, "rb") as f:
        iv = f.read()

    permutation = np.load(image_message.permutation_path)

    # Log encrypted image size
    try:
        encrypted_size = os.path.getsize(image_message.encrypted_image_path)
    except Exception:
        encrypted_size = len(encrypted_image) if encrypted_image is not None else None
    logger.info(f"[decrypt] message_id={message_id} encrypted_size={encrypted_size} bytes")

    # Decrypt AES key
    aeskey_start = time.perf_counter()
    decrypted_aes_key = decrypt_aes_key(encrypted_aes_key, private_key)
    aeskey_end = time.perf_counter()
    logger.info(f"[decrypt] message_id={message_id} rsa_decrypt_time={aeskey_end-aeskey_start:.4f}s")

    # Load the original image to get its shape
    original_image_path = f"data/images/{message_id}/original.jpg"
    original_shape = cv2.imread(original_image_path).shape

    # Decrypt image
    aesdec_start = time.perf_counter()
    decrypted_scrambled_image = aes_decrypt_image(encrypted_image, decrypted_aes_key, iv, original_shape)
    aesdec_end = time.perf_counter()
    logger.info(f"[decrypt] message_id={message_id} aes_decrypt_time={aesdec_end-aesdec_start:.4f}s")

    # Reverse chaotic scrambling
    scramble_rev_start = time.perf_counter()
    decrypted_image = reverse_logistic_map_biometric(decrypted_scrambled_image, permutation, original_shape)
    scramble_rev_end = time.perf_counter()
    logger.info(f"[decrypt] message_id={message_id} reverse_scramble_time={scramble_rev_end-scramble_rev_start:.4f}s")

    # Save decrypted image
    decrypted_image_path = f"data/images/{message_id}/decrypted.jpg"
    cv2.imwrite(decrypted_image_path, decrypted_image)

    # Log decrypted image size and total time
    try:
        decrypted_size = os.path.getsize(decrypted_image_path)
    except Exception:
        decrypted_size = None
    logger.info(f"[decrypt] message_id={message_id} decrypted_size={decrypted_size} bytes")

    logger.info(f"[decrypt] message_id={message_id} decryption_complete")

    # Clean up
    os.remove(temp_fingerprint_path)

    # Persist metrics for this decryption event
    try:
        decrypt_record = {
            "event": "decrypt",
            "message_id": message_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "encrypted_size": encrypted_size,
            "rsa_decrypt_time_s": round(aeskey_end - aeskey_start, 6),
            "aes_decrypt_time_s": round(aesdec_end - aesdec_start, 6),
            "reverse_scramble_time_s": round(scramble_rev_end - scramble_rev_start, 6),
            "decrypted_size": decrypted_size
        }
        append_stats(decrypt_record)
        # Also append a full combined record for decrypt event
        try:
            full_decrypt = {
                "event": "decrypt_full",
                "message_id": message_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "encrypted_path": image_message.encrypted_image_path,
                "decrypted_path": decrypted_image_path,
                "encrypted_size": encrypted_size,
                "decrypted_size": decrypted_size,
                "rsa_decrypt_time_s": round(aeskey_end - aeskey_start, 6),
                "aes_decrypt_time_s": round(aesdec_end - aesdec_start, 6),
                "reverse_scramble_time_s": round(scramble_rev_end - scramble_rev_start, 6)
            }
            append_all(full_decrypt)
        except Exception as e:
            logger.error(f"Failed to append full decrypt record: {e}")
    except Exception as e:
        logger.error(f"Failed to record decrypt metrics: {e}")

    # Return the decrypted image
    return FileResponse(decrypted_image_path, media_type="image/jpeg")


if __name__ == "__main__":
    uvicorn.run("secure_image_server:app", host="0.0.0.0", port=8000, reload=True)
