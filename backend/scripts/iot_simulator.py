import time
import random
import json
import redis
import os
import sqlite3
from datetime import datetime, timedelta

# Conexión local a Redis para publicar eventos IoT simulados
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
# Path a la base de datos (relativo al script)
db_path = os.path.join(os.path.dirname(__file__), "..", "acuityflow.db")
r = redis.from_url(redis_url, decode_responses=True)

ZONES = ["ER-Trauma", "ICU", "Triage", "Pediatrics"]

def create_random_shifts():
    """Inserta algunos turnos aleatorios para que el historial de staff no esté vacío."""
    try:
        if not os.path.exists(db_path):
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Solo insertamos si no hay muchos turnos
        cursor.execute("SELECT COUNT(*) FROM shifts")
        count = cursor.fetchone()[0]
        if count > 5:
            conn.close()
            return

        print("[Simulador] Generando historial de turnos de prueba...")
        cursor.execute("SELECT id FROM staff WHERE is_active = 1")
        staff_ids = [row[0] for row in cursor.fetchall()]
        
        if not staff_ids:
            conn.close()
            return

        for _ in range(15):
            s_id = random.choice(staff_ids)
            zone = random.choice(ZONES)
            # Fecha hace unos días/horas (entre 1 y 72 horas atrás)
            start_dt = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
            # SQLite por defecto guarda datetimes como strings ISO o formats compatibles
            cursor.execute(
                "INSERT INTO shifts (staff_id, zone, start_time) VALUES (?, ?, ?)",
                (s_id, zone, start_dt.strftime('%Y-%m-%d %H:%M:%S'))
            )
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al crear turnos de prueba: {e}")

def generate_telemetry():
    zone = random.choice(ZONES)
    
    # Aumentamos el rango de pacientes para forzar saturación (4 a 15)
    # Con un promedio más alto, es más probable llegar al 80% de Acuity
    patients = random.randint(4, 15)
    
    signals = []
    for i in range(patients):
        # Simulamos señales más inestables (probabilidad de 30% de ser grave)
        is_unstable = random.random() < 0.3
        
        if is_unstable:
            hr = random.randint(110, 160)
            o2 = random.randint(85, 93)
        else:
            hr = random.randint(60, 100)
            o2 = random.randint(95, 100)
        
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
    num_critical = sum(1 for s in signals if s['status'] == 'critical')
    print(f"[{time.strftime('%H:%M:%S')}] Telemetría -> {zone} ({patients} pac) | Críticos: {num_critical}")

if __name__ == "__main__":
    print("🚀 Iniciando Simulador de Dispositivos IoT v2.0 (Modo Test Feature Staff)...")
    
    # Paso 1: Intentar poblar historial para que el Panel de Staff se vea completo
    create_random_shifts()
    
    try:
        while True:
            generate_telemetry()
            # Simulamos datos cada 2 segundos (más dinámico para el dashboard)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nSimulador detenido.")
