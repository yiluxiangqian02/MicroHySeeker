"""Bayesian optimization utilities based on Optuna."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

import optuna

ParameterValue: TypeAlias = float | int | str | bool | None
Direction: TypeAlias = Literal["maximize", "minimize"]
ObjectiveFunction: TypeAlias = Callable[[dict[str, ParameterValue]], float]
MultiObjectiveFunction: TypeAlias = Callable[
    [dict[str, ParameterValue]], Sequence[float]
]


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(slots=True, frozen=True)
class ParameterDefinition:
    """A normalized search-space definition."""

    name: str
    kind: Literal["float", "int", "categorical"]
    low: float | int | None = None
    high: float | int | None = None
    choices: tuple[ParameterValue, ...] | None = None
    log: bool = False
    step: float | int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("parameter name cannot be empty")

        if self.kind in {"float", "int"}:
            if self.low is None or self.high is None:
                raise ValueError(f"{self.name}: low/high are required for {self.kind}")
            if self.low > self.high:
                raise ValueError(f"{self.name}: low cannot be greater than high")

        if self.kind == "categorical":
            if not self.choices:
                raise ValueError(f"{self.name}: choices cannot be empty")

        if self.kind == "float" and self.log and self.step is not None:
            raise ValueError(f"{self.name}: float parameter cannot use both log and step")

        if (
            self.kind == "int"
            and self.log
            and self.step is not None
            and int(self.step) != 1
        ):
            raise ValueError(
                f"{self.name}: int parameter with log=True only supports step=1"
            )

    def suggest(self, trial: optuna.Trial) -> ParameterValue:
        if self.kind == "float":
            kwargs: dict[str, Any] = {}
            if self.log:
                kwargs["log"] = True
            if self.step is not None:
                kwargs["step"] = float(self.step)
            return float(
                trial.suggest_float(
                    self.name,
                    float(self.low),
                    float(self.high),
                    **kwargs,
                )
            )

        if self.kind == "int":
            kwargs = {}
            if self.log:
                kwargs["log"] = True
            if self.step is not None:
                kwargs["step"] = int(self.step)
            return int(
                trial.suggest_int(
                    self.name,
                    int(self.low),
                    int(self.high),
                    **kwargs,
                )
            )

        if self.choices is None:
            raise ValueError(f"{self.name}: categorical choices are missing")
        return trial.suggest_categorical(self.name, list(self.choices))


class ParameterSpace:
    """Defines how Optuna should sample each parameter."""

    def __init__(
        self,
        parameters: Mapping[str, Any] | Iterable[ParameterDefinition] | None = None,
    ) -> None:
        self._definitions: list[ParameterDefinition] = []
        self._index: dict[str, ParameterDefinition] = {}

        if parameters is None:
            return

        if isinstance(parameters, Mapping):
            self.extend_from_mapping(parameters)
            return

        for definition in parameters:
            self.add(definition)

    def add(self, definition: ParameterDefinition) -> None:
        if definition.name in self._index:
            raise ValueError(f"duplicate parameter name: {definition.name}")
        self._definitions.append(definition)
        self._index[definition.name] = definition

    def add_float(
        self,
        name: str,
        low: float,
        high: float,
        *,
        log: bool = False,
        step: float | None = None,
    ) -> None:
        self.add(
            ParameterDefinition(
                name=name,
                kind="float",
                low=low,
                high=high,
                log=log,
                step=step,
            )
        )

    def add_int(
        self,
        name: str,
        low: int,
        high: int,
        *,
        log: bool = False,
        step: int | None = 1,
    ) -> None:
        self.add(
            ParameterDefinition(
                name=name,
                kind="int",
                low=low,
                high=high,
                log=log,
                step=step,
            )
        )

    def add_categorical(self, name: str, choices: Sequence[ParameterValue]) -> None:
        self.add(
            ParameterDefinition(name=name, kind="categorical", choices=tuple(choices))
        )

    def extend_from_mapping(self, config: Mapping[str, Any]) -> None:
        for name, spec in config.items():
            self._add_from_spec(name=name, spec=spec)

    def suggest(self, trial: optuna.Trial) -> dict[str, ParameterValue]:
        if not self._definitions:
            raise ValueError("parameter space is empty")
        return {definition.name: definition.suggest(trial) for definition in self._definitions}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(definition.name for definition in self._definitions)

    def __len__(self) -> int:
        return len(self._definitions)

    def _add_from_spec(self, name: str, spec: Any) -> None:
        if isinstance(spec, Mapping):
            kind = str(spec.get("type", "")).strip().lower()
            if kind in {"float", "continuous"}:
                self.add_float(
                    name=name,
                    low=float(spec["low"]),
                    high=float(spec["high"]),
                    log=bool(spec.get("log", False)),
                    step=float(spec["step"]) if spec.get("step") is not None else None,
                )
                return

            if kind in {"int", "integer"}:
                self.add_int(
                    name=name,
                    low=int(spec["low"]),
                    high=int(spec["high"]),
                    log=bool(spec.get("log", False)),
                    step=int(spec["step"]) if spec.get("step") is not None else 1,
                )
                return

            if kind in {"categorical", "choice"}:
                choices = spec.get("choices")
                if not isinstance(choices, Sequence) or isinstance(
                    choices, (str, bytes, bytearray)
                ):
                    raise TypeError(f"{name}: 'choices' must be a sequence")
                self.add_categorical(name=name, choices=choices)
                return

            raise ValueError(f"{name}: unknown parameter type '{kind}'")

        if isinstance(spec, Sequence) and not isinstance(spec, (str, bytes, bytearray)):
            values = list(spec)
            if len(values) == 2 and all(_is_numeric(value) for value in values):
                low, high = values
                if all(isinstance(value, int) and not isinstance(value, bool) for value in values):
                    self.add_int(name=name, low=int(low), high=int(high))
                else:
                    self.add_float(name=name, low=float(low), high=float(high))
                return

            if not values:
                raise ValueError(f"{name}: sequence specification cannot be empty")
            self.add_categorical(name=name, choices=values)
            return

        raise TypeError(f"{name}: unsupported parameter specification: {spec!r}")


@dataclass(slots=True, frozen=True)
class OptimizationResult:
    study: optuna.Study
    best_params: dict[str, ParameterValue]
    best_value: float
    best_trial_number: int
    total_trials: int


@dataclass(slots=True, frozen=True)
class MultiObjectiveOptimizationResult:
    study: optuna.Study
    pareto_params: list[dict[str, ParameterValue]]
    pareto_values: list[tuple[float, ...]]
    pareto_trial_numbers: list[int]
    total_trials: int


class BayesianOptimizer:
    """Single-objective Bayesian optimizer with Optuna TPE sampler."""

    def __init__(
        self,
        parameter_space: ParameterSpace | Mapping[str, Any],
        *,
        direction: Direction = "maximize",
        seed: int | None = None,
        sampler: optuna.samplers.BaseSampler | None = None,
        study_name: str | None = None,
        storage: str | None = None,
        load_if_exists: bool = False,
    ) -> None:
        self.parameter_space = (
            parameter_space
            if isinstance(parameter_space, ParameterSpace)
            else ParameterSpace(parameter_space)
        )
        self.direction = direction
        self.seed = seed
        self.study_name = study_name
        self.storage = storage
        self.load_if_exists = load_if_exists
        self._sampler = sampler or optuna.samplers.TPESampler(
            seed=seed,
            multivariate=True,
        )
        self._study: optuna.Study | None = None

    @property
    def study(self) -> optuna.Study:
        if self._study is None:
            raise RuntimeError("study not created yet; call optimize() first")
        return self._study

    def optimize(
        self,
        objective: ObjectiveFunction,
        n_trials: int,
        *,
        timeout: float | None = None,
        n_jobs: int = 1,
        show_progress_bar: bool = False,
        catch: tuple[type[Exception], ...] = (),
        reset_study: bool = True,
    ) -> OptimizationResult:
        if n_trials <= 0:
            raise ValueError("n_trials must be greater than 0")

        study = self._create_study() if reset_study or self._study is None else self._study

        def wrapped_objective(trial: optuna.Trial) -> float:
            params = self.parameter_space.suggest(trial)
            value = objective(params)
            return float(value)

        study.optimize(
            wrapped_objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=n_jobs,
            show_progress_bar=show_progress_bar,
            catch=catch,
        )
        self._study = study

        best_trial = study.best_trial
        return OptimizationResult(
            study=study,
            best_params=dict(best_trial.params),
            best_value=float(best_trial.value),
            best_trial_number=best_trial.number,
            total_trials=len(study.trials),
        )

    def _create_study(self) -> optuna.Study:
        return optuna.create_study(
            direction=self.direction,
            sampler=self._sampler,
            study_name=self.study_name,
            storage=self.storage,
            load_if_exists=self.load_if_exists,
        )


class MultiObjectiveBayesianOptimizer:
    """Multi-objective Bayesian optimizer with Optuna TPE sampler."""

    def __init__(
        self,
        parameter_space: ParameterSpace | Mapping[str, Any],
        *,
        directions: Sequence[Direction],
        seed: int | None = None,
        sampler: optuna.samplers.BaseSampler | None = None,
        study_name: str | None = None,
        storage: str | None = None,
        load_if_exists: bool = False,
    ) -> None:
        self.parameter_space = (
            parameter_space
            if isinstance(parameter_space, ParameterSpace)
            else ParameterSpace(parameter_space)
        )
        self.directions = tuple(directions)
        if len(self.directions) < 2:
            raise ValueError("multi-objective optimizer requires at least two directions")
        self.seed = seed
        self.study_name = study_name
        self.storage = storage
        self.load_if_exists = load_if_exists
        self._sampler = sampler or optuna.samplers.TPESampler(
            seed=seed,
            multivariate=True,
        )
        self._study: optuna.Study | None = None

    @property
    def study(self) -> optuna.Study:
        if self._study is None:
            raise RuntimeError("study not created yet; call optimize() first")
        return self._study

    def optimize(
        self,
        objective: MultiObjectiveFunction,
        n_trials: int,
        *,
        timeout: float | None = None,
        n_jobs: int = 1,
        show_progress_bar: bool = False,
        catch: tuple[type[Exception], ...] = (),
        reset_study: bool = True,
    ) -> MultiObjectiveOptimizationResult:
        if n_trials <= 0:
            raise ValueError("n_trials must be greater than 0")

        study = self._create_study() if reset_study or self._study is None else self._study

        def wrapped_objective(trial: optuna.Trial) -> list[float]:
            params = self.parameter_space.suggest(trial)
            values = objective(params)
            if len(values) != len(self.directions):
                raise ValueError(
                    "objective output size does not match directions: "
                    f"{len(values)} != {len(self.directions)}"
                )
            return [float(value) for value in values]

        study.optimize(
            wrapped_objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=n_jobs,
            show_progress_bar=show_progress_bar,
            catch=catch,
        )
        self._study = study

        pareto_trials = list(study.best_trials)
        pareto_values = [
            tuple(float(value) for value in (trial.values or ())) for trial in pareto_trials
        ]
        return MultiObjectiveOptimizationResult(
            study=study,
            pareto_params=[dict(trial.params) for trial in pareto_trials],
            pareto_values=pareto_values,
            pareto_trial_numbers=[trial.number for trial in pareto_trials],
            total_trials=len(study.trials),
        )

    def _create_study(self) -> optuna.Study:
        return optuna.create_study(
            directions=list(self.directions),
            sampler=self._sampler,
            study_name=self.study_name,
            storage=self.storage,
            load_if_exists=self.load_if_exists,
        )
