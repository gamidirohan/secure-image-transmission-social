"""
Simple test script to check if the FastAPI server is working.
"""

import requests

def test_health_endpoint():
    """Test the health endpoint."""
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing FastAPI server...")
    if test_health_endpoint():
        print("Server is running!")
    else:
        print("Server is not running or has an error.")
