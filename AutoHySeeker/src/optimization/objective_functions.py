"""Electrochemical objective functions for Bayesian optimization."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

NumericArray: TypeAlias = npt.NDArray[np.float64]
ResultPayload: TypeAlias = Mapping[str, Any] | Sequence[float] | NumericArray
ResultGetter: TypeAlias = Callable[[Mapping[str, Any]], ResultPayload]
ObjectiveCallable: TypeAlias = Callable[[Mapping[str, Any]], float]


def _as_array(values: Any, *, field_name: str) -> NumericArray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size == 0:
        raise ValueError(f"{field_name} cannot be empty")
    return array


class PeakCurrentObjective:
    """Objective that maximizes peak current from experimental results."""

    def __init__(
        self,
        result_getter: ResultGetter | None = None,
        *,
        peak_key: str = "peak_current",
        current_key: str = "current",
        use_absolute_peak: bool = True,
    ) -> None:
        self.result_getter = result_getter
        self.peak_key = peak_key
        self.current_key = current_key
        self.use_absolute_peak = use_absolute_peak

    def evaluate_result(self, result: ResultPayload) -> float:
        if isinstance(result, Mapping):
            if self.peak_key in result and result[self.peak_key] is not None:
                peak = float(result[self.peak_key])
                return abs(peak) if self.use_absolute_peak else peak

            if self.current_key not in result:
                raise KeyError(
                    f"result must contain '{self.peak_key}' or '{self.current_key}'"
                )
            values = result[self.current_key]
        else:
            values = result

        current = _as_array(values, field_name=self.current_key)
        if self.use_absolute_peak:
            return float(np.max(np.abs(current)))
        return float(np.max(current))

    def __call__(self, params: Mapping[str, Any]) -> float:
        if self.result_getter is None:
            raise RuntimeError("result_getter is required when objective is called with params")
        result = self.result_getter(params)
        return self.evaluate_result(result)


class SignalToNoiseObjective:
    """Objective that maximizes signal-to-noise ratio (SNR)."""

    def __init__(
        self,
        result_getter: ResultGetter | None = None,
        *,
        snr_key: str = "signal_to_noise",
        signal_key: str = "signal",
        noise_key: str = "noise",
        current_key: str = "current",
        baseline_fraction: float = 0.2,
        noise_floor: float = 1e-12,
        use_absolute_signal: bool = True,
    ) -> None:
        if baseline_fraction <= 0 or baseline_fraction > 1:
            raise ValueError("baseline_fraction must be within (0, 1]")
        if noise_floor <= 0:
            raise ValueError("noise_floor must be greater than 0")

        self.result_getter = result_getter
        self.snr_key = snr_key
        self.signal_key = signal_key
        self.noise_key = noise_key
        self.current_key = current_key
        self.baseline_fraction = baseline_fraction
        self.noise_floor = noise_floor
        self.use_absolute_signal = use_absolute_signal

    def evaluate_result(self, result: ResultPayload) -> float:
        if isinstance(result, Mapping):
            if self.snr_key in result and result[self.snr_key] is not None:
                return float(result[self.snr_key])

            if self.signal_key in result and self.noise_key in result:
                signal = float(result[self.signal_key])
                noise = abs(float(result[self.noise_key]))
                signal_value = abs(signal) if self.use_absolute_signal else signal
                return signal_value / max(noise, self.noise_floor)

            if self.current_key not in result:
                raise KeyError(
                    "result must contain one of "
                    f"'{self.snr_key}', ('{self.signal_key}', '{self.noise_key}') "
                    f"or '{self.current_key}'"
                )
            values = result[self.current_key]
        else:
            values = result

        current = _as_array(values, field_name=self.current_key)
        signal = float(np.max(np.abs(current)) if self.use_absolute_signal else np.max(current))
        window = max(3, int(round(current.size * self.baseline_fraction)))
        window = min(window, current.size)
        baseline = current[:window]
        noise = float(np.std(baseline, ddof=1 if baseline.size > 1 else 0))
        return signal / max(noise, self.noise_floor)

    def __call__(self, params: Mapping[str, Any]) -> float:
        if self.result_getter is None:
            raise RuntimeError("result_getter is required when objective is called with params")
        result = self.result_getter(params)
        return self.evaluate_result(result)


class MultiObjectiveFunction:
    """Combines multiple scalar objectives into one vector-valued objective."""

    def __init__(
        self,
        objectives: Sequence[ObjectiveCallable],
        names: Sequence[str] | None = None,
    ) -> None:
        if not objectives:
            raise ValueError("at least one objective is required")
        self.objectives = list(objectives)

        if names is None:
            self.names = tuple(f"objective_{idx + 1}" for idx in range(len(self.objectives)))
            return

        if len(names) != len(objectives):
            raise ValueError("names length must match objectives length")
        self.names = tuple(names)

    def evaluate(self, params: Mapping[str, Any]) -> tuple[float, ...]:
        return tuple(float(objective(params)) for objective in self.objectives)

    def evaluate_named(self, params: Mapping[str, Any]) -> dict[str, float]:
        values = self.evaluate(params)
        return {name: value for name, value in zip(self.names, values)}

    def __call__(self, params: Mapping[str, Any]) -> tuple[float, ...]:
        return self.evaluate(params)
