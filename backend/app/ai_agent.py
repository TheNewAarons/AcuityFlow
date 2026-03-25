import asyncio
from sqlalchemy.orm import Session
from . import models

async def trigger_autonomous_recruitment(zone: str, required_staff: int, db: Session):
    """
    Simula un Agente de IA autónomo. En lugar de reglas estáticas, este módulo interactuaría
    con un modelo fundacional (LLM) proporcionándole el contexto del hospital para que elija 
    a los candidatos idóneos y orqueste la comunicación.
    """
    print(f"\n🤖 [IA AGENT] ==== INICIANDO ORQUESTACIÓN ====")
    print(f"🤖 [IA AGENT] Detectado déficit crítico en {zone}. Misión: reclutar {required_staff} profesionales.")
    
    # 1. El Agente Inteligente busca personal disponible en la DB
    available_staff = db.query(models.Staff).filter(models.Staff.is_available == True).all()
    
    if not available_staff:
        print("🤖 [IA AGENT] CRÍTICO: No se encontraron candidatos en la base de datos de RR.HH.")
        print(f"🤖 [IA AGENT] ==== FIN DE ORQUESTACIÓN ====\n")
        return {"status": "Escalation Required (No beds/staff available)", "recruited": []}
        
    # 2. La IA evalúa y perfila candidatos. (Aquí simulamos seleccionando basados en necesidad)
    # Llama a un extra margen de candidatos (p. ej. el doble) para asegurar que algunos acepten
    selected_candidates = available_staff[:required_staff * 2] 
    
    recruited = []
    
    # 3. Orquestación Autónoma: El LLM redacta y envía mensajes SMS / Emails contextuales
    for candidate in selected_candidates:
        print(f"🤖 [IA AGENT] -> Contactando a {candidate.name} ({candidate.role}) vía SMS/Twilio...")
        await asyncio.sleep(1.5) # Simula retraso de la red y tiempo de "lectura" del empleado
        
        # Simular respuesta del empleado interactuando con el bot de RRHH (Ej: "Acepto" por WhatsApp)
        import random
        if random.random() > 0.4: # 60% probabilidad de aceptar
            print(f"   ✅ [RESPUESTA] {candidate.name}: 'Acepto el turno extra. Voy en camino.'")
            
            # Actualizar DB y panel de control vía IA
            candidate.is_available = False
            
            shift = models.Shift(
                staff_id=candidate.id,
                zone=zone
            )
            db.add(shift)
            
            recruited.append(candidate.name)
            
            # Si hemos llenado la vacante, paramos de spammear otros empleados
            if len(recruited) >= required_staff:
                print(f"🤖 [IA AGENT] Cupo lleno. Cancelando mensajes pendientes a otros candidatos.")
                break
        else:
            print(f"   ❌ [RESPUESTA] {candidate.name}: 'Lo siento, no puedo cubrir el turno hoy.'")
            
    db.commit()
    
    print(f"🤖 [IA AGENT] Resumen de Misión: Reclutados {len(recruited)} de {required_staff}.")
    print(f"🤖 [IA AGENT] ==== FIN DE ORQUESTACIÓN ====\n")
    
    if len(recruited) >= required_staff:
        return {"status": "Success", "message": "Déficit resuelto exitosamente", "recruited": recruited}
    elif len(recruited) > 0:
        return {"status": "Partial", "message": "Se logró mitigación parcial", "recruited": recruited}
    else:
        return {"status": "Failed", "message": "Nadie aceptó el turno", "recruited": []}
