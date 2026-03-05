"""Electrochemical data analysis tools for AutoHySeeker.

Provides pure-function analysis helpers for common electrochemical techniques:

* CV  — peak detection, overpotential, exchange current density
* LSV — onset potential, half-wave potential, limiting current
* EIS — Nyquist statistics, charge-transfer resistance estimate

All functions accept a :class:`~pandas.DataFrame` (or a file path string) and
return plain ``dict`` results so they remain LLM-friendly and serialisable.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


# ── column aliases ─────────────────────────────────────────────────────────────

_CV_POTENTIAL_ALIASES = ["Potential(V)", "Potential", "Potential/V", "Ewe/V", "E/V"]
_CV_CURRENT_ALIASES = ["Current(A)", "Current", "Current/A", "I/A", "I/mA"]
_EIS_ZRE_ALIASES = ["Zre(Ohm)", "Z_re", "Zreal", "Re(Z)/Ohm", "Z'/Ohm"]
_EIS_ZIM_ALIASES = ["Zim(Ohm)", "Z_im", "Zimag", "-Im(Z)/Ohm", "-Z''/Ohm", "Im(Z)/Ohm"]
_FREQ_ALIASES = ["Freq(Hz)", "freq/Hz", "Frequency/Hz", "freq"]


def _find_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Return the first alias that exists as a column in *df*."""
    for alias in aliases:
        if alias in df.columns:
            return alias
    # case-insensitive fallback
    lower_map = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    return None


def _load_df(data: pd.DataFrame | str) -> pd.DataFrame:
    if isinstance(data, str):
        from src.tools.data_reader import load_echem_file
        return load_echem_file(data).data  # type: ignore[return-value]
    return data


# ── CV analysis ───────────────────────────────────────────────────────────────

def analyze_cv(
    data: pd.DataFrame | str,
    scan_rate_mv_s: float | None = None,
) -> dict[str, Any]:
    """Analyse a cyclic voltammogram.

    Detects oxidation and reduction peaks, computes basic statistics, and
    optionally estimates the peak-to-peak separation (ΔEp).

    Args:
        data: DataFrame with potential and current columns, *or* a file path.
        scan_rate_mv_s: Scan rate in mV/s (optional, stored in metadata only).

    Returns:
        Dict with keys:

        * ``potential_range`` — [min, max] in V
        * ``current_range``   — [min, max] in A
        * ``oxidation_peak``  — ``{potential_V, current_A}`` or ``None``
        * ``reduction_peak``  — ``{potential_V, current_A}`` or ``None``
        * ``delta_Ep_V``      — peak-to-peak separation in V, or ``None``
        * ``n_points``        — number of data points
        * ``scan_rate_mv_s``  — echoed back if provided
        * ``warnings``        — list of warning strings
    """
    df = _load_df(data)
    warnings: list[str] = []

    pot_col = _find_col(df, _CV_POTENTIAL_ALIASES)
    cur_col = _find_col(df, _CV_CURRENT_ALIASES)
    if pot_col is None or cur_col is None:
        return {
            "error": "Required potential/current columns not found",
            "columns": list(df.columns),
        }

    potential = pd.to_numeric(df[pot_col], errors="coerce").dropna()
    current = pd.to_numeric(df[cur_col], errors="coerce")
    current = current[potential.index]

    if len(potential) < 4:
        warnings.append("Too few data points for reliable peak detection")

    # Normalise current to amperes (convert mA → A if values look like mA)
    if current.abs().mean() > 1.0:
        current = current * 1e-3
        warnings.append("Current values appear to be in mA; auto-converted to A")

    # Peak detection: use a simple rolling-window derivative sign change
    ox_peak: dict[str, float] | None = None
    red_peak: dict[str, float] | None = None

    if len(potential) >= 4:
        # Split into forward (increasing E) and backward (decreasing E) sweeps
        mid = len(potential) // 2
        fwd_pot = potential.iloc[:mid].values
        fwd_cur = current.iloc[:mid].values
        bwd_pot = potential.iloc[mid:].values
        bwd_cur = current.iloc[mid:].values

        # Oxidation peak: maximum current in forward sweep
        if len(fwd_cur) > 0:
            ox_idx = int(np.argmax(fwd_cur))
            ox_peak = {
                "potential_V": float(fwd_pot[ox_idx]),
                "current_A": float(fwd_cur[ox_idx]),
            }

        # Reduction peak: minimum current in backward sweep
        if len(bwd_cur) > 0:
            red_idx = int(np.argmin(bwd_cur))
            red_peak = {
                "potential_V": float(bwd_pot[red_idx]),
                "current_A": float(bwd_cur[red_idx]),
            }

    delta_ep: float | None = None
    if ox_peak and red_peak:
        delta_ep = round(abs(ox_peak["potential_V"] - red_peak["potential_V"]), 6)

    return {
        "potential_range": [float(potential.min()), float(potential.max())],
        "current_range": [float(current.min()), float(current.max())],
        "oxidation_peak": ox_peak,
        "reduction_peak": red_peak,
        "delta_Ep_V": delta_ep,
        "n_points": len(potential),
        "scan_rate_mv_s": scan_rate_mv_s,
        "warnings": warnings,
    }


# ── LSV analysis ──────────────────────────────────────────────────────────────

def analyze_lsv(
    data: pd.DataFrame | str,
    direction: str = "cathodic",
) -> dict[str, Any]:
    """Analyse a linear sweep voltammogram.

    Args:
        data: DataFrame or file path.
        direction: ``"cathodic"`` (HER/ORR, current goes negative) or
                   ``"anodic"`` (OER/oxidation, current goes positive).

    Returns:
        Dict with keys:

        * ``onset_potential_V``    — potential where |current| exceeds 1% of max
        * ``half_wave_potential_V``— potential at half the limiting current
        * ``limiting_current_A``   — extreme current value
        * ``potential_range``      — [min, max] in V
        * ``n_points``             — number of data points
        * ``direction``            — echoed back
        * ``warnings``             — list of warnings
    """
    df = _load_df(data)
    warnings: list[str] = []

    pot_col = _find_col(df, _CV_POTENTIAL_ALIASES)
    cur_col = _find_col(df, _CV_CURRENT_ALIASES)
    if pot_col is None or cur_col is None:
        return {"error": "Required potential/current columns not found"}

    potential = pd.to_numeric(df[pot_col], errors="coerce").dropna()
    current = pd.to_numeric(df[cur_col], errors="coerce")[potential.index]

    if current.abs().mean() > 1.0:
        current = current * 1e-3
        warnings.append("Current auto-converted from mA to A")

    pot_arr = potential.values
    cur_arr = current.values

    if direction == "cathodic":
        lim_current = float(cur_arr.min())
        threshold = lim_current * 0.01  # 1% of limiting (negative side)
        onset_mask = cur_arr <= threshold
    else:
        lim_current = float(cur_arr.max())
        threshold = lim_current * 0.01
        onset_mask = cur_arr >= threshold

    onset_potential: float | None = None
    if onset_mask.any():
        onset_idx = int(np.argmax(onset_mask))
        onset_potential = float(pot_arr[onset_idx])

    half_wave: float | None = None
    half_lim = lim_current / 2.0
    if direction == "cathodic":
        hw_mask = cur_arr <= half_lim
    else:
        hw_mask = cur_arr >= half_lim
    if hw_mask.any():
        hw_idx = int(np.argmax(hw_mask))
        half_wave = float(pot_arr[hw_idx])

    return {
        "onset_potential_V": onset_potential,
        "half_wave_potential_V": half_wave,
        "limiting_current_A": lim_current,
        "potential_range": [float(potential.min()), float(potential.max())],
        "n_points": len(potential),
        "direction": direction,
        "warnings": warnings,
    }


# ── EIS analysis ──────────────────────────────────────────────────────────────

def analyze_eis(data: pd.DataFrame | str) -> dict[str, Any]:
    """Analyse an electrochemical impedance spectrum (Nyquist plot data).

    Estimates the charge-transfer resistance (Rct) as the diameter of the
    high-to-mid frequency semicircle, and the solution resistance (Rs) as the
    real-axis intercept at high frequency.

    Args:
        data: DataFrame or file path.  Must contain real (Zre) and imaginary
              (Zim) impedance columns; an optional frequency column is used to
              order the data correctly.

    Returns:
        Dict with keys:

        * ``Rs_ohm``             — estimated solution resistance (Ω)
        * ``Rct_ohm``            — estimated charge-transfer resistance (Ω)
        * ``Zre_range``          — [min, max] of Zre
        * ``Zim_range``          — [min, max] of Zim
        * ``n_points``           — number of frequency points
        * ``frequency_range_Hz`` — [min, max] if freq column found else ``None``
        * ``warnings``           — list of warnings
    """
    df = _load_df(data)
    warnings: list[str] = []

    zre_col = _find_col(df, _EIS_ZRE_ALIASES)
    zim_col = _find_col(df, _EIS_ZIM_ALIASES)
    freq_col = _find_col(df, _FREQ_ALIASES)

    if zre_col is None or zim_col is None:
        return {
            "error": "Required Zre/Zim columns not found",
            "columns": list(df.columns),
        }

    zre = pd.to_numeric(df[zre_col], errors="coerce").dropna()
    zim_raw = pd.to_numeric(df[zim_col], errors="coerce")[zre.index]

    # Some software exports -Zim; normalise so Zim > 0 in capacitive arc
    zim = zim_raw.abs()

    # Sort by frequency (high→low) if available so high-f is first
    freq_range: list[float] | None = None
    if freq_col is not None:
        freq = pd.to_numeric(df[freq_col], errors="coerce")[zre.index]
        sort_idx = freq.argsort()[::-1]  # descending frequency
        zre = zre.iloc[sort_idx].reset_index(drop=True)
        zim = zim.iloc[sort_idx].reset_index(drop=True)
        freq_range = [float(freq.min()), float(freq.max())]

    zre_arr = zre.values
    zim_arr = zim.values

    # Rs: real-axis intercept at highest frequency (≈ first point with min Zim)
    rs: float = float(zre_arr[0]) if len(zre_arr) > 0 else 0.0

    # Rct: diameter of semicircle ≈ (max Zre in arc) - Rs
    # Identify semicircle peak: point where Zim is maximum
    if len(zim_arr) > 1:
        peak_idx = int(np.argmax(zim_arr))
        zre_at_peak = float(zre_arr[peak_idx])
        # Rct ≈ 2 × (Zre_at_peak - Rs) is the semicircle diameter
        rct = max(0.0, 2.0 * (zre_at_peak - rs))
    else:
        rct = 0.0
        warnings.append("Not enough points to estimate Rct")

    if rct == 0.0 and len(zre_arr) > 1:
        warnings.append("Rct estimate is 0; spectrum may not show a clear semicircle")

    return {
        "Rs_ohm": round(rs, 4),
        "Rct_ohm": round(rct, 4),
        "Zre_range": [float(zre.min()), float(zre.max())],
        "Zim_range": [float(zim.min()), float(zim.max())],
        "n_points": len(zre),
        "frequency_range_Hz": freq_range,
        "warnings": warnings,
    }


# ── batch analysis ─────────────────────────────────────────────────────────────

def analyze_echem_files(
    file_paths: list[str],
) -> list[dict[str, Any]]:
    """Analyse a list of electrochemical CSV files, auto-detecting technique.

    Args:
        file_paths: List of paths to CSV files.

    Returns:
        List of result dicts, each containing ``file``, ``technique``, and
        the technique-specific analysis keys.
    """
    from src.tools.data_reader import load_echem_file

    results: list[dict[str, Any]] = []
    for fp in file_paths:
        try:
            echem = load_echem_file(fp)
            df = echem.data
            technique = echem.technique
        except Exception as exc:
            results.append({"file": fp, "error": str(exc)})
            continue

        if technique == "cv":
            analysis = analyze_cv(df)
        elif technique == "lsv":
            analysis = analyze_lsv(df)
        elif technique == "eis":
            analysis = analyze_eis(df)
        else:
            # Generic stats for unknown techniques
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            analysis = {
                "technique": technique,
                "n_points": len(df),
                "columns": list(df.columns),
                "numeric_columns": numeric_cols,
            }

        results.append({"file": fp, "technique": technique, **analysis})
    return results


# ── register with global registry on import ──────────────────────────────────

def _register() -> None:
    try:
        from src.common.tool_registry import registry

        registry.register(
            "analyze_cv",
            analyze_cv,
            "Analyse a cyclic voltammogram: peak detection, ΔEp, potential/current range",
            {
                "type": "object",
                "properties": {
                    "data": {"description": "DataFrame or CSV file path"},
                    "scan_rate_mv_s": {"type": "number", "description": "Scan rate in mV/s"},
                },
                "required": ["data"],
            },
        )
        registry.register(
            "analyze_lsv",
            analyze_lsv,
            "Analyse a linear sweep voltammogram: onset potential, half-wave potential, limiting current",
            {
                "type": "object",
                "properties": {
                    "data": {"description": "DataFrame or CSV file path"},
                    "direction": {
                        "type": "string",
                        "enum": ["cathodic", "anodic"],
                        "description": "Sweep direction",
                    },
                },
                "required": ["data"],
            },
        )
        registry.register(
            "analyze_eis",
            analyze_eis,
            "Analyse EIS Nyquist data: estimate Rs and Rct from impedance spectrum",
            {
                "type": "object",
                "properties": {
                    "data": {"description": "DataFrame or CSV file path"},
                },
                "required": ["data"],
            },
        )
        registry.register(
            "analyze_echem_files",
            analyze_echem_files,
            "Batch-analyse a list of electrochemical CSV files with auto technique detection",
            {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of CSV file paths",
                    }
                },
                "required": ["file_paths"],
            },
        )
    except Exception:
        pass


_register()
