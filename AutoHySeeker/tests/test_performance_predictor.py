from __future__ import annotations


def _make_experiments(count: int) -> list[dict]:
    experiments: list[dict] = []
    for index in range(count):
        fe = 0.2 + 0.01 * index
        co = 0.5 - 0.005 * index
        ni = 1.0 - fe - co
        experiments.append(
            {
                "params": {"Fe": round(fe, 4), "Co": round(co, 4), "Ni": round(ni, 4)},
                "metrics": {"overpotential_mV": round(220 - index * 1.8, 4)},
            }
        )
    return experiments


def test_predictor_not_ready_below_minimum_points() -> None:
    from src.ml.performance_predictor import PerformancePredictor

    predictor = PerformancePredictor()
    result = predictor.fit(_make_experiments(8))

    assert result["ready"] is False
    assert predictor.predict_candidates(5) == []


def test_predictor_selects_random_forest_band() -> None:
    from src.ml.performance_predictor import PerformancePredictor

    predictor = PerformancePredictor()
    result = predictor.fit(_make_experiments(12))
    candidates = predictor.predict_candidates(5)

    assert result["ready"] is True
    assert result["model_type"] == "random_forest"
    assert len(candidates) == 5
    assert abs(sum(candidates[0]["params"].values()) - 1.0) < 1e-5


def test_predictor_selects_gaussian_process_band() -> None:
    from src.ml.performance_predictor import PerformancePredictor

    predictor = PerformancePredictor()
    result = predictor.fit(_make_experiments(32))
    candidates = predictor.predict_candidates(3)

    assert result["ready"] is True
    assert result["model_type"] == "gaussian_process"
    assert len(candidates) == 3
    assert "uncertainty" in candidates[0]
