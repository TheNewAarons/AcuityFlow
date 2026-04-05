from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from . import models, database
from .acuity_engine import calculate_weighted_workload
from .digital_twin import simulate_what_if
from .ai_agent import trigger_autonomous_recruitment, get_agent_logs
from .auth import verify_password, create_access_token, get_current_user, check_role
import redis.asyncio as redis_async
import asyncio
import json
import os
from dotenv import load_dotenv

# Load .env before other imports that might depend on it
load_dotenv()

import datetime
from .auth import SECRET_KEY

from .auth import get_password_hash

async def seed_db():
    async with database.SessionLocal() as db:
        # Seed Users (RBAC)
        result = await db.execute(select(models.User))
        if not result.scalars().first():
            users_data_keys = [
                ("admin", "admin@acuityflow.com", "ADMIN", models.UserRole.ADMIN),
                ("nurse_jackie", "jackie@staff.com", "NURSE", models.UserRole.CHIEF_NURSE),
                ("dr_house", "house@staff.com", "DOCTOR", models.UserRole.DOCTOR)
            ]
            for username, email, pwd_key, role in users_data_keys:
                # Use environment variables if available, otherwise fallback to coded (still better than plain text in code)
                # In production, these MUST be in env.
                pwd = os.getenv(f"SEED_PWD_{username.upper()}", "AcuityFlow!2024")
                db.add(models.User(
                    username=username, 
                    email=email, 
                    hashed_password=get_password_hash(pwd), 
                    role=role
                ))

        # Seed Staff
        result = await db.execute(select(models.Staff))
        existing_staff = result.scalars().all()
        if len(existing_staff) == 0:
            names = ["Dr. House", "Dr. Cuddy", "Nurse Jackie", "Carla E.", "Dr. Carter", "Nurse Hathaway", "Dr. Cox", "J.D.", "Turk", "Elliot Reid"]
            roles = ["Doctor"] * 4 + ["RN"] * 6
            test_phone = os.getenv("TEST_PHONE_NUMBER", "+1234567890")
            for name, role in zip(names, roles):
                db.add(models.Staff(name=name, role=role, phone_number=test_phone))
        else:
            for staff in existing_staff:
                staff.is_available = True

        # Seed Zones
        result = await db.execute(select(models.PatientZone))
        if len(result.scalars().all()) == 0:
            zones_data = [
                {"name": "ER-Trauma", "capacity": 10},
                {"name": "ICU", "capacity": 8},
                {"name": "Triage", "capacity": 15},
                {"name": "Pediatrics", "capacity": 12}
            ]
            for z in zones_data:
                db.add(models.PatientZone(name=z["name"], capacity=z["capacity"]))

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

# Cache simple para capacidades de zona para evitar hits constantes a la DB
zone_capacity_cache = {}

async def get_zone_capacity(zone_name: str):
    if zone_name in zone_capacity_cache:
        return zone_capacity_cache[zone_name]

    async with database.SessionLocal() as db:
        result = await db.execute(select(models.PatientZone).filter(models.PatientZone.name == zone_name))
        zone = result.scalars().first()
        if zone:
            zone_capacity_cache[zone_name] = zone.capacity
            return zone.capacity
    return 10 # Fallback

async def redis_listener():
    """ 
    Tarea de fondo (Background Task) que escucha centralizadamente a Redis 
    y hace push a los WebSockets. Evita crear N instancias de PubSub.
    """
    redis_client = redis_async.from_url(redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    history_buffer = []
    BATCH_SIZE = 10

    while True:
        try:
            await pubsub.subscribe("acuity_telemetry")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])

                    # Capacidad dinámica desde DB/Cache
                    capacity = await get_zone_capacity(data["zone"])

                    score = calculate_weighted_workload(capacity, data["patient_count"], data["signals"])
                    payload = {
                        "zone": data["zone"],
                        "acuity_score": score,
                        "patient_count": data["patient_count"],
                        "status": "critical" if score >= 80 else "warning" if score >= 60 else "stable",
                        "timestamp": data["timestamp"]
                    }
                    
                    # Buffer de Persistencia Histórica
                    history_buffer.append(models.ZoneHistory(
                        zone=data["zone"],
                        timestamp=data["timestamp"],
                        acuity_score=score,
                        patient_count=data["patient_count"]
                    ))

                    if len(history_buffer) >= BATCH_SIZE:
                        async with database.SessionLocal() as db_session:
                            db_session.add_all(history_buffer)
                            await db_session.commit()
                        history_buffer = []
                        
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
        
    # Validar configuración de seguridad
    if not SECRET_KEY:
        print("❌ CRITICAL: JWT_SECRET_KEY not set in environment!")
        # Stop in production, warn in dev
        if os.getenv("ENV") == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set in production")
        else:
            print("⚠️ WARNING: Using insecure development session. Set JWT_SECRET_KEY for security.")
        
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
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AcuityFlow Engine Running (Async DB Mode + Global Redis Pool)"}

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login", response_model=Token)
async def login(req: LoginRequest, db: AsyncSession = Depends(database.get_db)):
    # Simple form_data body for JSON
    username = req.username
    password = req.password
    
    result = await db.execute(select(models.User).filter(models.User.username == username))
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.hashed_password):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "username": user.username,
        "role": user.role
    }

@app.get("/api/auth/me")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }

@app.get("/api/staff")
async def get_staff(
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(get_current_user)
):
    """
    Returns staff list. Phone numbers (PII) are masked for non-authorized roles.
    """
    try:
        result = await db.execute(select(models.Staff).filter(models.Staff.is_active == True))
        staff_members = result.scalars().all()
        
        # Privacy Mapping
        can_see_pii = user.role in [models.UserRole.ADMIN, models.UserRole.CHIEF_NURSE]
        
        staff_data = []
        for s in staff_members:
            s_dict = {
                "id": s.id,
                "name": s.name,
                "role": s.role,
                "efficiency_multiplier": s.efficiency_multiplier,
                "is_available": s.is_available
            }
            if can_see_pii:
                s_dict["phone_number"] = s.phone_number
            else:
                s_dict["phone_number"] = "REDACTED"
            staff_data.append(s_dict)
            
        return staff_data
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
async def run_simulation(
    request: SimulationRequest, 
    user: models.User = Depends(check_role([models.UserRole.ADMIN, models.UserRole.CHIEF_NURSE]))
):
    events_dict = [e.model_dump() for e in request.events]
    result = simulate_what_if(request.base_state, events_dict)
    return {"projections": result}

class AgentTriggerReq(BaseModel):
    zone: str
    required_staff: int

@app.post("/api/agent/trigger")
async def api_trigger_agent(
    req: AgentTriggerReq, 
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(check_role([models.UserRole.ADMIN]))
):
    result = await trigger_autonomous_recruitment(req.zone, req.required_staff, db)
    return result

@app.get("/api/agent/logs")
async def api_get_agent_logs():
    return get_agent_logs()


# ─────────────────────────────────────────────────────────────
# STAFF MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────

class StaffCreate(BaseModel):
    name: str
    role: str
    phone_number: str  # Required: needed for AI recruitment notifications
    efficiency_multiplier: float = 1.0

class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone_number: Optional[str] = None
    efficiency_multiplier: Optional[float] = None

@app.patch("/api/staff/{staff_id}/availability")
async def toggle_staff_availability(
    staff_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(check_role([models.UserRole.ADMIN, models.UserRole.CHIEF_NURSE]))
):
    """Toggle is_available for a staff member. Accessible to Admin and Chief Nurse."""
    result = await db.execute(
        select(models.Staff).filter(models.Staff.id == staff_id, models.Staff.is_active == True)
    )
    staff = result.scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    staff.is_available = not staff.is_available
    await db.commit()
    return {"id": staff.id, "name": staff.name, "is_available": staff.is_available}

@app.post("/api/staff", status_code=201)
async def create_staff(
    data: StaffCreate,
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(check_role([models.UserRole.ADMIN]))
):
    """Create a new staff member. Admin only."""
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if not data.phone_number.strip():
        raise HTTPException(status_code=400, detail="Phone number is required for AI recruitment")
    new_staff = models.Staff(
        name=data.name.strip(),
        role=data.role,
        phone_number=data.phone_number.strip(),
        efficiency_multiplier=max(0.5, min(2.0, data.efficiency_multiplier)),
        is_available=True,
        is_active=True
    )
    db.add(new_staff)
    await db.commit()
    await db.refresh(new_staff)
    return {
        "id": new_staff.id,
        "name": new_staff.name,
        "role": new_staff.role,
        "phone_number": new_staff.phone_number,
        "efficiency_multiplier": new_staff.efficiency_multiplier,
        "is_available": new_staff.is_available
    }

@app.put("/api/staff/{staff_id}")
async def update_staff(
    staff_id: int,
    data: StaffUpdate,
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(check_role([models.UserRole.ADMIN]))
):
    """Edit staff details. Admin only."""
    result = await db.execute(
        select(models.Staff).filter(models.Staff.id == staff_id, models.Staff.is_active == True)
    )
    staff = result.scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    if data.name is not None:
        staff.name = data.name.strip()
    if data.role is not None:
        staff.role = data.role
    if data.phone_number is not None:
        staff.phone_number = data.phone_number.strip()
    if data.efficiency_multiplier is not None:
        staff.efficiency_multiplier = max(0.5, min(2.0, data.efficiency_multiplier))
    await db.commit()
    return {
        "id": staff.id,
        "name": staff.name,
        "role": staff.role,
        "phone_number": staff.phone_number,
        "efficiency_multiplier": staff.efficiency_multiplier,
        "is_available": staff.is_available
    }

@app.delete("/api/staff/{staff_id}")
async def delete_staff(
    staff_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(check_role([models.UserRole.ADMIN]))
):
    """Soft-delete a staff member (is_active=False). Preserves Shift history. Admin only."""
    result = await db.execute(select(models.Staff).filter(models.Staff.id == staff_id))
    staff = result.scalars().first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    staff.is_active = False
    await db.commit()
    return {"status": "deleted", "id": staff_id}

@app.get("/api/staff/{staff_id}/shifts")
async def get_staff_shifts(
    staff_id: int,
    db: AsyncSession = Depends(database.get_db),
    user: models.User = Depends(get_current_user)
):
    """Get the last 10 shifts for a specific staff member."""
    from sqlalchemy import desc as sa_desc
    result = await db.execute(
        select(models.Shift)
        .filter(models.Shift.staff_id == staff_id)
        .order_by(sa_desc(models.Shift.start_time))
        .limit(10)
    )
    shifts = result.scalars().all()
    return [
        {
            "id": s.id,
            "zone": s.zone,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
        }
        for s in shifts
    ]

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
