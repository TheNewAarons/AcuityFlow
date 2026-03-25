from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from . import models, database
from .acuity_engine import calculate_weighted_workload
from .digital_twin import simulate_what_if
from .ai_agent import trigger_autonomous_recruitment
import redis.asyncio as redis_async
import asyncio
import json
import os

async def seed_db():
    async with database.SessionLocal() as db:
        result = await db.execute(select(models.Staff))
        existing = result.scalars().all()
        if len(existing) == 0:
            names = ["Dr. House", "Dr. Cuddy", "Nurse Jackie", "Carla E.", "Dr. Carter", "Nurse Hathaway", "Dr. Cox", "J.D.", "Turk", "Elliot Reid"]
            roles = ["Doctor"] * 4 + ["RN"] * 6
            for name, role in zip(names, roles):
                db.add(models.Staff(name=name, role=role))
        else:
            # Reset availability on every startup so the pool never stays depleted
            for staff in existing:
                staff.is_available = True
        await db.commit()

# --- REDIS CONNECTION MANAGER & BROADCASTER ---
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # Transmitir a todas las conexiones activas
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

async def redis_listener():
    """ 
    Tarea de fondo (Background Task) que escucha centralizadamente a Redis 
    y hace push a los WebSockets. Evita crear N instancias de PubSub.
    """
    redis_client = redis_async.from_url(redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    while True:
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
                    
                    # Persistencia Histórica (Time-Series Local DB)
                    async with database.SessionLocal() as db_session:
                        history = models.ZoneHistory(
                            zone=data["zone"],
                            timestamp=data["timestamp"],
                            acuity_score=score,
                            patient_count=data["patient_count"]
                        )
                        db_session.add(history)
                        await db_session.commit()
                        
                    await manager.broadcast(json.dumps(payload))
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Error en el Listener global de Redis: {e}. Reintentando en 5s...")
            await asyncio.sleep(5)
        finally:
            try:
                await pubsub.unsubscribe("acuity_telemetry")
            except: 
                pass

redis_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_task
    try:
        # Inicialización segura asíncrona de las tablas
        async with database.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        await seed_db()
    except Exception as e:
        print(f"Error inicializando base de datos asíncrona: {e}")
        
    # Iniciar el Single-Threaded Redis Listener global
    redis_task = asyncio.create_task(redis_listener())
    
    yield
    
    # Limpieza al apagar la aplicación
    if redis_task:
        redis_task.cancel()
        try:
            await redis_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="AcuityFlow API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AcuityFlow Engine Running (Async DB Mode + Global Redis Pool)"}

@app.get("/api/staff")
async def get_staff(db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(select(models.Staff))
        return result.scalars().all()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/staff/reset")
async def reset_staff_availability(db: AsyncSession = Depends(database.get_db)):
    """Resets all staff to available=True so the recruitment pool is restored."""
    try:
        result = await db.execute(select(models.Staff))
        staff_list = result.scalars().all()
        for s in staff_list:
            s.is_available = True
        await db.commit()
        return {"status": "ok", "reset": len(staff_list)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/zones")
async def get_zones(db: AsyncSession = Depends(database.get_db)):
    try:
        result = await db.execute(select(models.PatientZone))
        return result.scalars().all()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/history/all")
async def get_all_history(limit: int = 20, db: AsyncSession = Depends(database.get_db)):
    """ 
    Recupera los últimos N registros generados en la base histórica estacionaria 
    para poder re-dibujar el historial del hospital tras un F5 (Recargo de página).
    """
    from sqlalchemy import desc
    try:
        # Obtenemos una ventana representativa (N = 20 puntos por zona)
        result = await db.execute(
            select(models.ZoneHistory)
            .order_by(desc(models.ZoneHistory.timestamp))
            .limit(limit * 4) 
        )
        records = result.scalars().all()
        history = {}
        # Invertimos para que el tiempo fluya de Izquierda (pasado) a Derecha (presente)
        for r in reversed(records):
            if r.zone not in history: 
                history[r.zone] = []
            
            # Formateamos timestamp
            from datetime import datetime
            dt = datetime.fromtimestamp(r.timestamp).strftime('%H:%M:%S')
            history[r.zone].append({"time": dt, "acuity_score": r.acuity_score})
            if len(history[r.zone]) > limit: 
                history[r.zone].pop(0)
                
        return history
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
async def api_trigger_agent(req: AgentTriggerReq, db: AsyncSession = Depends(database.get_db)):
    result = await trigger_autonomous_recruitment(req.zone, req.required_staff, db)
    return result

# WebSocket endpoint V2 optimizado (1 conexión Redis para N clientes Web)
@app.websocket("/ws/acuity")
async def websocket_acuity(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantener la conexión abierta y esperar si el cliente manda algo
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
