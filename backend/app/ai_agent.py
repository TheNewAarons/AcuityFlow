import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models

async def trigger_autonomous_recruitment(zone: str, required_staff: int, db: AsyncSession):
    """
    Simula un Agente de IA autónomo. En lugar de reglas estáticas, este módulo interactuaría
    con un modelo fundacional (LLM).
    Refactorizado V2: Usa un Event Loop asíncrono eficiente (AsyncSession).
    """
    print(f"\n🤖 [IA AGENT] ==== INICIANDO ORQUESTACIÓN ====")
    print(f"🤖 [IA AGENT] Detectado déficit crítico en {zone}. Misión: reclutar {required_staff} profesionales.")
    
    # 1. Búsqueda asíncrona y no bloqueante en DB
    result = await db.execute(select(models.Staff).filter(models.Staff.is_available == True))
    available_staff = result.scalars().all()
    
    if not available_staff:
        print("🤖 [IA AGENT] CRÍTICO: No se encontraron candidatos en la base de datos de RR.HH.")
        print(f"🤖 [IA AGENT] ==== FIN DE ORQUESTACIÓN ====\n")
        return {"status": "Escalation Required (No beds/staff available)", "recruited": []}
        
    # 2. IA evalúa candidatos
    selected_candidates = available_staff[:required_staff * 2] 
    
    recruited = []
    
    for candidate in selected_candidates:
        print(f"🤖 [IA AGENT] -> Contactando a {candidate.name} ({candidate.role})...")
        await asyncio.sleep(1.5)
        
        import random
        if random.random() > 0.4:
            print(f"   ✅ [RESPUESTA] {candidate.name}: 'Acepto el turno extra. Voy en camino.'")
            
            candidate.is_available = False
            
            shift = models.Shift(
                staff_id=candidate.id,
                zone=zone
            )
            db.add(shift)
            
            recruited.append(candidate.name)
            
            if len(recruited) >= required_staff:
                print(f"🤖 [IA AGENT] Cupo lleno. Cancelando mensajes pendientes a otros candidatos.")
                break
        else:
            print(f"   ❌ [RESPUESTA] {candidate.name}: 'Lo siento, no puedo cubrir el turno hoy.'")
            
    # Asíncronamente enviamos el commit a la base de datos sin trabar a FastApi
    await db.commit()
    
    print(f"🤖 [IA AGENT] Resumen de Misión: Reclutados {len(recruited)} de {required_staff}.")
    print(f"🤖 [IA AGENT] ==== FIN DE ORQUESTACIÓN ====\n")
    
    if len(recruited) >= required_staff:
        return {"status": "Success", "message": "Déficit resuelto exitosamente", "recruited": recruited}
    elif len(recruited) > 0:
        return {"status": "Partial", "message": "Se logró mitigación parcial", "recruited": recruited}
    else:
        return {"status": "Failed", "message": "Nadie aceptó el turno", "recruited": []}
