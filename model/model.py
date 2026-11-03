
"""Educational one-compartment phenylalanine simulator for PheTwin India.

This model is illustrative and is not validated for clinical decision-making.
Model parameters are loaded from params.json.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp


# Molecular weight used for unit conversion: phenylalanine, g/mol.
# Keep the conversion consistent throughout the project.
PHE_MW = 165.19

REQUIRED_PARAMETERS = {
    "body_weight_kg",
    "vd_l_per_kg",
    "km_mg_per_l",
    "fasting_c0_mg_per_l",
    "endogenous_input_mg_per_h",
    "k_alt_l_per_h",
    "ka_per_h",
    "bioavailability",
    "phe_mg_per_g_protein",
    "target_low_umol_l",
    "target_high_umol_l",
}


def load_params(path=None):
    """Load model parameter values from params.json."""
    raw = load_parameter_metadata(path)
    return {
        key: item["value"]
        for key, item in raw.items()
        if not key.startswith("_")
    }


def load_parameter_metadata(path=None):
    """Load parameter values together with their provenance metadata."""
    if path is None:
        path = Path(__file__).parent / "params.json"

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_parameter_metadata(raw)
    return raw


def validate_parameter_metadata(raw):
    """Validate parameter structure and physically meaningful demo ranges."""
    parameters = {key for key in raw if not key.startswith("_")}
    missing = REQUIRED_PARAMETERS - parameters
    if missing:
        raise ValueError(
            "Parameter file is missing required entries: "
            + ", ".join(sorted(missing))
        )

    for key in parameters:
        item = raw[key]
        if not isinstance(item, dict):
            raise ValueError(f"Parameter '{key}' must be an object.")

        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Parameter '{key}' must have a numeric value.")
        if not math.isfinite(value):
            raise ValueError(f"Parameter '{key}' must be finite.")

        citation = str(item.get("citation", "")).strip()
        if not citation:
            raise ValueError(f"Parameter '{key}' must have a citation field.")

    positive = {
        "body_weight_kg",
        "vd_l_per_kg",
        "km_mg_per_l",
        "fasting_c0_mg_per_l",
        "ka_per_h",
    }
    for key in positive:
        if raw[key]["value"] <= 0:
            raise ValueError(f"Parameter '{key}' must be positive.")

    non_negative = {
        "endogenous_input_mg_per_h",
        "k_alt_l_per_h",
        "phe_mg_per_g_protein",
        "target_low_umol_l",
        "target_high_umol_l",
    }
    for key in non_negative:
        if raw[key]["value"] < 0:
            raise ValueError(f"Parameter '{key}' must be non-negative.")

    bioavailability = raw["bioavailability"]["value"]
    if not 0 <= bioavailability <= 1:
        raise ValueError("Parameter 'bioavailability' must be between 0 and 1.")

    if raw["target_low_umol_l"]["value"] > raw["target_high_umol_l"]["value"]:
        raise ValueError("Target low concentration cannot exceed target high concentration.")


def unresolved_parameter_citations(path=None):
    """Return non-private parameters with missing or placeholder citations."""
    raw = load_parameter_metadata(path)
    unresolved = []

    for key, item in raw.items():
        if key.startswith("_"):
            continue
        citation = str(item.get("citation", "")).strip()
        if not citation or "TO_FILL" in citation.upper():
            unresolved.append(key)

    return unresolved


def target_range_metadata(path=None):
    """Return target-range values and context notes for transparent display."""
    raw = load_parameter_metadata(path)
    return {
        "low": {
            "value": raw["target_low_umol_l"]["value"],
            "context": raw["target_low_umol_l"].get("context", ""),
        },
        "high": {
            "value": raw["target_high_umol_l"]["value"],
            "context": raw["target_high_umol_l"].get("context", ""),
        },
    }


def mgl_to_umol(concentration_mg_l):
    """Convert concentration from mg/L to micromol/L."""
    return concentration_mg_l / PHE_MW * 1000.0


def mgl_to_mgdl(concentration_mg_l):
    """Convert concentration from mg/L to mg/dL."""
    return concentration_mg_l / 10.0


def calibrate_vmax(
    endogenous_input, fasting_concentration, km, k_alt_l_per_h=0.0
):
    """Calculate reference PAH capacity at the configured fasting state.

    Calibration matches the full model's steady-state equation:
    ``endogenous_input = Vmax*C/(Km+C) + k_alt*C``.
    ``k_alt_l_per_h`` defaults to zero for compatibility with the simplified
    equation, but callers using the full model must pass the configured value.
    """
    if endogenous_input <= 0 or fasting_concentration <= 0 or km <= 0:
        raise ValueError("Input, fasting concentration, and Km must be positive.")
    if k_alt_l_per_h < 0:
        raise ValueError("Alternative clearance must be non-negative.")

    residual_input = endogenous_input - k_alt_l_per_h * fasting_concentration
    if residual_input < 0:
        raise ValueError(
            "Alternative clearance exceeds endogenous input at the fasting target."
        )

    return residual_input * (km + fasting_concentration) / fasting_concentration


def steady_state_conc(vmax_eff, params):
    """Calculate fasting steady-state concentration in mg/L."""
    endogenous = params["endogenous_input_mg_per_h"]
    km = params["km_mg_per_l"]
    k_alt = params["k_alt_l_per_h"]

    if endogenous < 0 or km <= 0 or k_alt < 0 or vmax_eff < 0:
        raise ValueError("Model rates must be non-negative and Km must be positive.")

    # Solve:
    # endogenous = Vmax_eff*C/(Km+C) + k_alt*C
    if k_alt == 0:
        if vmax_eff <= endogenous:
            return np.inf
        return endogenous * km / (vmax_eff - endogenous)

    a = k_alt
    b = vmax_eff + k_alt * km - endogenous
    c = -endogenous * km
    discriminant = b**2 - 4 * a * c

    if discriminant < 0:
        raise ValueError("No real steady-state concentration for these parameters.")

    return (-b + np.sqrt(discriminant)) / (2 * a)


def simulate(meals, activity_pct, p=None, t_end=24.0, dt=0.05):
    """Simulate blood Phe over time.

    Args:
        meals: list of (time_h, phe_mg), e.g. [(8, 400), (13, 600)].
        activity_pct: illustrative residual PAH activity, from 0 to 100.
        p: optional dictionary of parameter values.
        t_end: simulation duration in hours.
        dt: output time step in hours.

    Returns:
        DataFrame with time, concentrations, gut Phe, and cumulative
        elimination. Meal Phe values are illustrative model inputs.
    """
    p = p or load_params()

    if not 0 <= activity_pct <= 100:
        raise ValueError("activity_pct must be between 0 and 100.")
    if t_end <= 0 or dt <= 0:
        raise ValueError("t_end and dt must be positive.")

    for time_h, phe_mg in meals:
        if time_h < 0 or time_h > t_end or phe_mg < 0:
            raise ValueError("Meals must have valid times and non-negative Phe.")

    volume_l = p["body_weight_kg"] * p["vd_l_per_kg"]
    if volume_l <= 0:
        raise ValueError("Distribution volume must be positive.")

    vmax_normal = calibrate_vmax(
        p["endogenous_input_mg_per_h"],
        p["fasting_c0_mg_per_l"],
        p["km_mg_per_l"],
        p["k_alt_l_per_h"],
    )
    vmax_eff = vmax_normal * activity_pct / 100.0

    endogenous = p["endogenous_input_mg_per_h"]
    km = p["km_mg_per_l"]
    k_alt = p["k_alt_l_per_h"]
    ka = p["ka_per_h"]
    bioavailability = p["bioavailability"]

    if ka <= 0 or not 0 <= bioavailability <= 1:
        raise ValueError("ka must be positive and bioavailability must be 0–1.")

    def rhs(_time, state):
        gut_mg, body_mg, eliminated_mg = state
        concentration = max(body_mg, 0.0) / volume_l

        pah_elimination = vmax_eff * concentration / (km + concentration)
        alternative_elimination = k_alt * concentration
        elimination = pah_elimination + alternative_elimination

        return [
            -ka * gut_mg,
            ka * gut_mg + endogenous - elimination,
            elimination,
        ]

    starting_concentration = steady_state_conc(vmax_eff, p)
    if not np.isfinite(starting_concentration):
        raise ValueError(
            "The selected activity has no finite fasting steady state "
            "under these parameters."
        )

    # State variables: gut Phe (mg), body-pool Phe (mg), eliminated Phe (mg).
    state = [0.0, starting_concentration * volume_l, 0.0]
    meal_events = sorted(meals, key=lambda meal: meal[0])

    # Integrate between meal times so a meal enters the gut at its scheduled time.
    event_times = sorted(set([0.0, t_end] + [t for t, _ in meal_events]))
    output_rows = []

    meals_by_time = {}
    for time_h, phe_mg in meal_events:
        meals_by_time[time_h] = meals_by_time.get(time_h, 0.0) + phe_mg

    for index, start in enumerate(event_times):
        if start in meals_by_time:
            state[0] += bioavailability * meals_by_time[start]

        if index == len(event_times) - 1:
            break

        end = event_times[index + 1]
        if end <= start:
            continue

        sample_times = np.arange(start, end, dt)
        sample_times = np.append(sample_times, end)

        solution = solve_ivp(
            rhs,
            (start, end),
            state,
            t_eval=sample_times,
            method="LSODA",
            rtol=1e-8,
            atol=1e-8,
        )

        if not solution.success:
            raise RuntimeError(f"Simulation failed: {solution.message}")

        segment = solution.y.T
        if output_rows:
            segment = segment[1:]  # Avoid duplicate boundary time points.
        output_rows.extend(
            (time_h, row.copy())
            for time_h, row in zip(solution.t, segment)
        )
        state = solution.y[:, -1].tolist()

    times = np.array([row[0] for row in output_rows])
    states = np.array([row[1] for row in output_rows])

    concentrations = states[:, 1] / volume_l

    return pd.DataFrame(
        {
            "t_h": times,
            "conc_mg_l": concentrations,
            "conc_umol_l": mgl_to_umol(concentrations),
            "conc_mg_dl": mgl_to_mgdl(concentrations),
            "gut_mg": states[:, 0],
            "eliminated_mg": states[:, 2],
        }
    )


def activity_from_tolerance(tolerance_mg_per_day, c_target_umol, p=None):
    """Estimate model residual activity from a proposed Phe tolerance.

    Calibration helper only. It requires literature-supported tolerance
    and target inputs before scientific interpretation.
    """
    p = p or load_params()

    if tolerance_mg_per_day < 0 or c_target_umol <= 0:
        raise ValueError("Tolerance must be non-negative and target must be positive.")

    concentration = c_target_umol * PHE_MW / 1000.0
    inflow = (
        p["endogenous_input_mg_per_h"]
        + p["bioavailability"] * tolerance_mg_per_day / 24.0
    )

    vmax_eff = (
        inflow - p["k_alt_l_per_h"] * concentration
    ) * (p["km_mg_per_l"] + concentration) / concentration

    vmax_normal = calibrate_vmax(
        p["endogenous_input_mg_per_h"],
        p["fasting_c0_mg_per_l"],
        p["km_mg_per_l"],
        p["k_alt_l_per_h"],
    )

    activity_pct = 100.0 * vmax_eff / vmax_normal
    if not 0 <= activity_pct <= 100:
        raise ValueError(
            "Tolerance implies residual activity outside the model's 0–100% range."
        )

    return activity_pct
