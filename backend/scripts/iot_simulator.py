import time
import random
import json
import redis
import os

# Conexión local a Redis para publicar eventos IoT simulados
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.from_url(redis_url, decode_responses=True)

def check_redis():
    try:
        r.ping()
        return True
    except redis.exceptions.ConnectionError:
        return False

ZONES = ["ER-Trauma", "ICU", "Triage", "Pediatrics"]

def generate_telemetry():
    zone = random.choice(ZONES)
    # Suponiendo que hay entre 2 y 12 pacientes por zona
    patients = random.randint(2, 12)
    
    signals = []
    for i in range(patients):
        # Simulamos señales de monitores
        hr = random.randint(55, 145) # Heart Rate
        o2 = random.randint(88, 100) # SpO2
        
        status = "stable"
        if hr > 120 or o2 < 92:
            status = "warning"
        if hr > 135 or o2 < 90:
            status = "critical"
            
        signals.append({"patient_id": f"P-{i}", "heart_rate": hr, "spo2": o2, "status": status})
        
    payload = {
        "zone": zone,
        "patient_count": patients,
        "signals": signals,
        "timestamp": time.time()
    }
    
    # Publicar en canal de Redis
    r.publish("acuity_telemetry", json.dumps(payload))
    print(f"[{time.strftime('%H:%M:%S')}] Publicada telemetría para {zone} ({patients} pacientes)")

if __name__ == "__main__":
    print("Iniciando simulador de dispositivos IoT (Monitores)...")
    try:
        while True:
            generate_telemetry()
            # Simulamos datos cada 3 segundos
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nSimulador detenido.")
