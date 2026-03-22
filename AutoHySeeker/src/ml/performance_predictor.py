"""Lightweight performance predictor for composition-to-metric modeling."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any

import optuna

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel

    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    RandomForestRegressor = None  # type: ignore[assignment]
    GaussianProcessRegressor = None  # type: ignore[assignment]
    RBF = None  # type: ignore[assignment]
    WhiteKernel = None  # type: ignore[assignment]
    _SKLEARN_AVAILABLE = False


@dataclass
class _TrainingPoint:
    params: dict[str, float]
    target: float


class PerformancePredictor:
    """Predict catalyst performance and propose candidate experiments."""

    def __init__(
        self,
        *,
        target_metric: str = "overpotential_mV",
        direction: str = "minimize",
        model_type: str = "auto",
        random_state: int = 42,
    ) -> None:
        self.target_metric = target_metric
        self.direction = direction
        self.model_type = model_type
        self.random_state = random_state
        self.selected_model_type = "not_ready"
        self.feature_names: list[str] = []
        self.training_points: list[_TrainingPoint] = []
        self.search_space: dict[str, tuple[float, float]] = {}
        self.is_ready = False
        self._model: Any = None

    def fit(self, experiments: list[dict[str, Any]]) -> dict[str, Any]:
        """Fit or update the predictor from experiment history."""
        points = self._extract_training_points(experiments)
        self.training_points = points
        self.feature_names = sorted({key for point in points for key in point.params})
        self.search_space = self._infer_search_space(points)

        if len(points) < 10 or not self.feature_names:
            self.selected_model_type = "not_ready"
            self.is_ready = False
            self._model = None
            return {"ready": False, "data_points": len(points), "model_type": self.selected_model_type}

        selected = self._select_model_type(len(points))
        self.selected_model_type = selected
        self.is_ready = True
        self._model = self._build_model(selected, points)
        return {"ready": True, "data_points": len(points), "model_type": self.selected_model_type}

    def predict_candidates(self, n_candidates: int = 10) -> list[dict[str, Any]]:
        """Generate candidate compositions with predicted value and uncertainty."""
        if not self.is_ready or not self.feature_names or n_candidates <= 0:
            return []

        sampler = optuna.samplers.TPESampler(seed=self.random_state)
        study = optuna.create_study(direction="minimize", sampler=sampler)
        candidates: list[dict[str, Any]] = []

        for _ in range(n_candidates):
            trial = study.ask()
            params = {
                feature: trial.suggest_float(feature, *self.search_space[feature])
                for feature in self.feature_names
            }
            params = self._normalize_params(params)
            predicted_value, uncertainty = self._predict_point(params)
            objective = predicted_value if self.direction == "minimize" else -predicted_value
            study.tell(trial, objective)
            candidates.append(
                {
                    "params": params,
                    "predicted_value": round(predicted_value, 4),
                    "uncertainty": round(uncertainty, 4),
                    "model_type": self.selected_model_type,
                }
            )

        reverse = self.direction == "maximize"
        candidates.sort(key=lambda item: item["predicted_value"], reverse=reverse)
        return candidates

    def _extract_training_points(self, experiments: list[dict[str, Any]]) -> list[_TrainingPoint]:
        points: list[_TrainingPoint] = []
        for experiment in experiments:
            params = experiment.get("params", {})
            metrics = experiment.get("metrics", {})
            target = metrics.get(self.target_metric)
            if not isinstance(params, dict) or target is None:
                continue
            numeric_params = {
                str(key): float(value)
                for key, value in params.items()
                if isinstance(value, (int, float))
            }
            if not numeric_params:
                continue
            points.append(_TrainingPoint(params=numeric_params, target=float(target)))
        return points

    def _infer_search_space(self, points: list[_TrainingPoint]) -> dict[str, tuple[float, float]]:
        search_space: dict[str, tuple[float, float]] = {}
        for feature in {key for point in points for key in point.params}:
            values = [point.params.get(feature, 0.0) for point in points]
            minimum = max(0.0, min(values))
            maximum = min(1.0, max(values))
            if minimum == maximum:
                minimum = max(0.0, minimum - 0.05)
                maximum = min(1.0, maximum + 0.05)
            search_space[feature] = (minimum, maximum)
        return search_space

    def _select_model_type(self, data_points: int) -> str:
        if self.model_type != "auto":
            return self.model_type
        if data_points > 30:
            return "gaussian_process"
        return "random_forest"

    def _build_model(self, model_type: str, points: list[_TrainingPoint]) -> Any:
        if _SKLEARN_AVAILABLE and model_type == "random_forest":
            model = RandomForestRegressor(
                n_estimators=64,
                random_state=self.random_state,
            )
            model.fit(self._matrix(points), [point.target for point in points])
            return model

        if _SKLEARN_AVAILABLE and model_type == "gaussian_process":
            kernel = RBF(length_scale=0.2) + WhiteKernel(noise_level=1e-4)
            model = GaussianProcessRegressor(
                kernel=kernel,
                random_state=self.random_state,
                normalize_y=True,
            )
            model.fit(self._matrix(points), [point.target for point in points])
            return model

        return {"points": points}

    def _predict_point(self, params: dict[str, float]) -> tuple[float, float]:
        vector = [params.get(feature, 0.0) for feature in self.feature_names]

        if _SKLEARN_AVAILABLE and self.selected_model_type == "random_forest" and hasattr(self._model, "estimators_"):
            tree_predictions = [float(estimator.predict([vector])[0]) for estimator in self._model.estimators_]
            mean_value = sum(tree_predictions) / len(tree_predictions)
            variance = sum((item - mean_value) ** 2 for item in tree_predictions) / len(tree_predictions)
            return mean_value, sqrt(variance)

        if _SKLEARN_AVAILABLE and self.selected_model_type == "gaussian_process" and hasattr(self._model, "predict"):
            predicted, std = self._model.predict([vector], return_std=True)
            return float(predicted[0]), float(std[0])

        return self._predict_with_surrogate(params)

    def _predict_with_surrogate(self, params: dict[str, float]) -> tuple[float, float]:
        weighted_sum = 0.0
        weight_total = 0.0
        targets: list[float] = []

        for point in self.training_points:
            distance = sqrt(
                sum(
                    (params.get(feature, 0.0) - point.params.get(feature, 0.0)) ** 2
                    for feature in self.feature_names
                )
            )
            weight = 1.0 / (distance + 1e-6)
            weighted_sum += point.target * weight
            weight_total += weight
            targets.append(point.target)

        mean_value = weighted_sum / weight_total if weight_total else 0.0
        mean_target = sum(targets) / len(targets)
        variance = sum((value - mean_target) ** 2 for value in targets) / len(targets)
        return mean_value, sqrt(variance)

    def _normalize_params(self, params: dict[str, float]) -> dict[str, float]:
        total = sum(max(value, 0.0) for value in params.values())
        if total <= 0:
            equal_share = round(1.0 / len(params), 6)
            return {key: equal_share for key in params}

        normalized = {key: max(value, 0.0) / total for key, value in params.items()}
        drift = 1.0 - sum(normalized.values())
        first_key = next(iter(normalized))
        normalized[first_key] += drift
        return {key: round(value, 6) for key, value in normalized.items()}

    def _matrix(self, points: list[_TrainingPoint]) -> list[list[float]]:
        return [
            [point.params.get(feature, 0.0) for feature in self.feature_names]
            for point in points
        ]
