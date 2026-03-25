def calculate_weighted_workload(base_capacity: int, patient_count: int, signals: list) -> float:
    """
    Calcula el "Acuity Score" (0.0 a 100.0) de un área, donde >80 es saturación crítica.
    En lugar de un simple ratio paciente/enfermera, evaluamos la agudeza (gravedad) de las señales IoT.
    """
    if base_capacity <= 0:
        return 100.0
    
    # Base load calculada por el ratio simple
    base_load = (patient_count / base_capacity) * 40.0
    
    # Carga ponderada añadida por gravedad clínica
    severity_load = 0.0
    
    for signal in signals:
        status = signal.get("status", "stable")
        # Si un paciente está inestable requiere mucho más esfuerzo de la enfermería que 1 paciente estable
        if status == "warning":
            severity_load += 5.0
        elif status == "critical":
            severity_load += 15.0
            
        # Factores extra: Ej. un ritmo cardíaco alto constante necesita monitoreo continuo
        hr = signal.get("heart_rate", 80)
        if hr > 130:
            severity_load += 3.0
            
    total_score = base_load + severity_load
    
    # Nunca devolver más de 100% de la métrica (o podríamos permitir >100% para sobrecarga masiva)
    # Por ahora limitamos a 100.0 visualmente, o podemos devolver score crudo (ej. 120.0 = desbordamiento!)
    
    return min(round(total_score, 1), 100.0)
