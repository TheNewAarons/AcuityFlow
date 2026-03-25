from app.acuity_engine import calculate_weighted_workload

def test_calculate_weighted_workload_basic():
    # 5 patients, capacity 10, all stable
    signals = [{"status": "stable", "heart_rate": 80} for _ in range(5)]
    score = calculate_weighted_workload(10, 5, signals)
    # (5/10) * 40 = 20.0
    assert score == 20.0

def test_calculate_weighted_workload_severity():
    # 2 patients, capacity 10, one critical
    signals = [
        {"status": "critical", "heart_rate": 140},
        {"status": "stable", "heart_rate": 80}
    ]
    score = calculate_weighted_workload(10, 2, signals)
    # base_load = (2/10) * 40 = 8.0
    # severity_load = 15.0 (critical) + 3.0 (hr > 130) = 18.0
    # total = 26.0
    assert score == 26.0

def test_calculate_weighted_workload_dynamic_capacity():
    # 5 patients, capacity 5, all stable
    signals = [{"status": "stable", "heart_rate": 80} for _ in range(5)]
    score = calculate_weighted_workload(5, 5, signals)
    # (5/5) * 40 = 40.0
    assert score == 40.0

    # same patients, capacity 20
    score_low = calculate_weighted_workload(20, 5, signals)
    # (5/20) * 40 = 10.0
    assert score_low == 10.0

def test_calculate_weighted_workload_cap():
    # Massive load
    signals = [{"status": "critical", "heart_rate": 150} for _ in range(10)]
    score = calculate_weighted_workload(5, 10, signals)
    # base_load = (10/5) * 40 = 80
    # severity = 10 * (15 + 3) = 180
    # total = 260
    # Should be capped at 100.0
    assert score == 100.0
