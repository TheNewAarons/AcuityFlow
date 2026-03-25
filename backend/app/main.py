from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
from . import models, database
from .acuity_engine import calculate_weighted_workload
from .digital_twin import simulate_what_if
from .ai_agent import trigger_autonomous_recruitment
import redis.asyncio as redis_async
import asyncio
import json
import os

# Crear tablas en DB 
# En producción sería ideal usar Alembic para migraciones
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"No se pudo conectar a la base de datos o inicializar tablas: {e}")

# Database Seeder (Datos de prueba para el agente)
def seed_db():
    db = database.SessionLocal()
    if db.query(models.Staff).count() == 0:
        import random
        names = ["Dr. House", "Dr. Cuddy", "Nurse Jackie", "Carla E.", "Dr. Carter", "Nurse Hathaway", "Dr. Cox", "J.D.", "Turk", "Elliot Reid"]
        roles = ["Doctor"] * 4 + ["RN"] * 6
        for name, role in zip(names, roles):
            db.add(models.Staff(name=name, role=role))
        db.commit()
    db.close()

try:
    seed_db()
except Exception as e:
    pass

app = FastAPI(title="AcuityFlow API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Expandir dominios en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AcuityFlow Engine Running"}

@app.get("/api/staff")
def get_staff(db: Session = Depends(database.get_db)):
    try:
        results = db.query(models.Staff).all()
        return results
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/zones")
def get_zones(db: Session = Depends(database.get_db)):
    try:
        results = db.query(models.PatientZone).all()
        return results
    except Exception as e:
        return {"error": str(e)}

class WhatIfEvent(BaseModel):
    zone: str
    add_patients: int
    severity_multiplier: float

class SimulationRequest(BaseModel):
    base_state: List[Dict[str, Any]]
    events: List[WhatIfEvent]

@app.post("/api/simulate")
def run_simulation(request: SimulationRequest):
    events_dict = [e.model_dump() for e in request.events]
    result = simulate_what_if(request.base_state, events_dict)
    return {"projections": result}

class AgentTriggerReq(BaseModel):
    zone: str
    required_staff: int

@app.post("/api/agent/trigger")
async def api_trigger_agent(req: AgentTriggerReq, db: Session = Depends(database.get_db)):
    result = await trigger_autonomous_recruitment(req.zone, req.required_staff, db)
    return result

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

# WebSocket para orquestar la comunicación de demanda de agudeza real (IoT -> Redis -> WebSockets)
@app.websocket("/ws/acuity")
async def websocket_acuity(websocket: WebSocket):
    await websocket.accept()
    redis_client = redis_async.from_url(redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    try:
        await pubsub.subscribe("acuity_telemetry")
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                score = calculate_weighted_workload(10, data["patient_count"], data["signals"])
                payload = {
                    "zone": data["zone"],
                    "acuity_score": score,
                    "patient_count": data["patient_count"],
                    "status": "critical" if score >= 80 else "warning" if score >= 60 else "stable",
                    "timestamp": data["timestamp"]
                }
                await websocket.send_text(json.dumps(payload))
    except Exception as e:
        print(f"Error en WebSocket Acuity (Probablemente Redis apagado): {e}")
        try:
            await websocket.send_text(json.dumps({"error": "Falló conexión al sistema de telemetría"}))
        except:
            pass
    finally:
        try:
            await pubsub.unsubscribe("acuity_telemetry")
        except:
            pass
        await pubsub.close()
        await redis_client.aclose()
