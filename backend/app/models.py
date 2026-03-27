from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import datetime
import enum
from .database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CHIEF_NURSE = "nurse"
    DOCTOR = "doctor"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.DOCTOR)
    is_active = Column(Boolean, default=True)
    
    # Relación opcional con Staff
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    staff = relationship("Staff")

class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String) # Ej: RN (Enfermera Registrada), Doctor, Técnico
    efficiency_multiplier = Column(Float, default=1.0)
    is_available = Column(Boolean, default=True)
    phone_number = Column(String, nullable=True) # Twilio/WhatsApp contact
    shifts = relationship("Shift", back_populates="staff")

class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"))
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    zone = Column(String) # Ej: Zona de Trauma, Triage, etc.
    
    staff = relationship("Staff", back_populates="shifts")

class PatientZone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    current_acuity_score = Column(Float, default=0.0) # Indicador de severidad de carga (basado en IoT)
    capacity = Column(Integer, default=10) # Capacidad base de camas/pacientes

class ZoneHistory(Base):
    """
    Simula una Time-Series Database (TSDB). En producción, usaríamos TimescaleDB o InfluxDB.
    Guarda los latidos históricos para pintar gráficas en el UI.
    """
    __tablename__ = "zone_history"
    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String, index=True)
    timestamp = Column(Float, index=True) # Epoch time
    acuity_score = Column(Float)
    patient_count = Column(Integer)
