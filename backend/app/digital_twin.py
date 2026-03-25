from .acuity_engine import calculate_weighted_workload

def simulate_what_if(base_state: list, what_if_events: list) -> list:
    """
    Simula la evolución de la carga basándose en el estado actual y eventos inyectados.
    base_state: = [{"zone": "ER-Trauma", "patients": 10}, ...]
    what_if_events: = [{"zone": "ER-Trauma", "add_patients": 5, "severity_multiplier": 1.5}]
    Retorna proyecciones de acuity_score.
    """
    projections = []
    
    # Mapear eventos por zona para facilidad de acceso
    events_by_zone = {}
    for event in what_if_events:
        events_by_zone[event["zone"]] = event
    
    for state in base_state:
        zone = state.get("zone")
        patients = state.get("patients", 0)
        
        # Estado base simulado: asumimos todos estables si no hay datos específicos de severidad base
        signals_simulated = [{"status": "stable", "heart_rate": 80} for _ in range(patients)]
        
        # Procesar si hay evento inyectado para esta zona
        if zone in events_by_zone:
            event = events_by_zone[zone]
            added = event.get("add_patients", 0)
            patients += added
            severity = event.get("severity_multiplier", 1.0)
            
            # Crear pacientes más graves según el multiplicador de severidad del evento
            for _ in range(added):
                if severity > 1.2:
                    signals_simulated.append({"status": "critical", "heart_rate": 140})
                elif severity > 1.0:
                    signals_simulated.append({"status": "warning", "heart_rate": 110})
                else:
                    signals_simulated.append({"status": "stable", "heart_rate": 80})
        
        # Calcular proyección
        # Nota: Idealmente deberíamos inyectar capacidades reales aquí también
        # Para mantener el prototipo simple, usamos un mapa de capacidades comunes
        CAPACITIES = {"ER-Trauma": 10, "ICU": 8, "Triage": 15, "Pediatrics": 12}
        cap = CAPACITIES.get(zone, 10)

        projected_score = calculate_weighted_workload(base_capacity=cap, patient_count=patients, signals=signals_simulated)
        
        projections.append({
            "zone": zone,
            "projected_patients": patients,
            "projected_score": projected_score,
            "status": "critical" if projected_score >= 80 else "warning" if projected_score >= 60 else "stable"
        })
        
    return projections
