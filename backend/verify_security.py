import requests
import os
import sys
from dotenv import load_dotenv

# Load security environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"

def verify_security():
    print("🔍 Starting Security Verification...")
    
    # 1. Test Login (Generic Error)
    print("\n1. Testing Generic Error Message on Failure...")
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "nonexistent", "password": "wrong"})
    # The backend still returns "Usuario o contraseña incorrectos", but the frontend is now generic too.
    # We check if it returns 401.
    print(f"   Status: {resp.status_code} (Expected 401)")
    
    # 2. Get Tokens for PII Test
    print("\n2. Getting tokens for PII Visibility Test...")
    admin_pwd = os.getenv("SEED_PWD_ADMIN", "AcuityFlow!2024")
    doctor_pwd = os.getenv("SEED_PWD_DOCTOR", "AcuityFlow!2024")
    
    admin_login = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": admin_pwd})
    doctor_login = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "dr_house", "password": doctor_pwd})
    
    if admin_login.status_code != 200 or doctor_login.status_code != 200:
        print("   ❌ Error: Could not login with seeded users. Did you set SEED_PWD_... env vars?")
        return

    admin_token = admin_login.json()["access_token"]
    doctor_token = doctor_login.json()["access_token"]

    # 3. Test Admin PII Visibility
    print("\n3. Testing Admin PII Visibility...")
    resp = requests.get(f"{BASE_URL}/api/staff", headers={"Authorization": f"Bearer {admin_token}"})
    staff = resp.json()
    has_pii = any(s.get("phone_number") and s["phone_number"] != "REDACTED" for s in staff)
    print(f"   Admin can see phone numbers: {has_pii} (Expected True)")

    # 4. Test User (Doctor) PII Masking
    print("\n4. Testing Doctor PII Masking (Privacy Check)...")
    resp = requests.get(f"{BASE_URL}/api/staff", headers={"Authorization": f"Bearer {doctor_token}"})
    staff = resp.json()
    all_masked = all(s.get("phone_number") == "REDACTED" for s in staff)
    print(f"   Doctor sees 'REDACTED': {all_masked} (Expected True)")

    # 5. Test CORS (Simulated by Origin header if server allows it)
    print("\n5. Testing CORS restriction...")
    # This is harder to test via requests as CORS is a browser feature, but we can check headers.
    resp = requests.options(f"{BASE_URL}/api/staff", headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "GET"})
    allow_origin = resp.headers.get("Access-Control-Allow-Origin")
    print(f"   CORS Access-Control-Allow-Origin for evil.com: {allow_origin} (Expected None or restricted)")

if __name__ == "__main__":
    verify_security()
