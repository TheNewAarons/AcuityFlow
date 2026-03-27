import requests
import time

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    print("--- 1. Testing Login as Admin ---")
    login_data = {"username": "admin", "password": "admin123"}
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if resp.status_code != 200:
        print(f"FAILED LOGIN: {resp.text}")
        return
    
    admin_token = resp.json()["access_token"]
    print(f"SUCCESS: Admin logged in. Token found.")

    print("\n--- 2. Testing RBAC: Admin triggering agent ---")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.post(f"{BASE_URL}/api/agent/trigger", json={"zone": "ICU", "required_staff": 1}, headers=headers)
    print(f"Admin trigger result: {resp.status_code} (Expected 200)")

    print("\n--- 3. Testing Login as Doctor ---")
    login_data = {"username": "dr_house", "password": "house123"}
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    doctor_token = resp.json()["access_token"]
    print(f"SUCCESS: Doctor logged in.")

    print("\n--- 4. Testing RBAC: Doctor triggering agent (Should fail) ---")
    headers = {"Authorization": f"Bearer {doctor_token}"}
    resp = requests.post(f"{BASE_URL}/api/agent/trigger", json={"zone": "ICU", "required_staff": 1}, headers=headers)
    print(f"Doctor trigger result: {resp.status_code} (Expected 403)")

    print("\n--- 5. Testing RBAC: Doctor simulating incident (Should fail) ---")
    sim_data = {
        "base_state": [{"zone": "ICU", "patients": 5}],
        "events": [{"zone": "ICU", "add_patients": 10, "severity_multiplier": 2.0}]
    }
    resp = requests.post(f"{BASE_URL}/api/simulate", json=sim_data, headers=headers)
    print(f"Doctor simulation result: {resp.status_code} (Expected 403)")

if __name__ == "__main__":
    # Note: This script requires the backend to be running.
    # We'll just print instructions if it fails connection.
    try:
        test_auth_flow()
    except requests.exceptions.ConnectionError:
        print("\nERROR: Backend no está corriendo. Inicia el servidor con 'npm run dev' o 'uvicorn app.main:app' para probar.")
