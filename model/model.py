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


PHE_MW = 165.19  # Phenylalanine molecular weight, g/mol.

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
    """Load parameter values from params.json."""
    raw = load_parameter_metadata(path)
    return {
        key: item["value"]
        for key, item in raw.items()
        if not key.startswith("_")
    }


def load_parameter_metadata(path=None):
    """Load parameter values together with provenance metadata."""
    if path is None:
        path = Path(__file__).parent / "params.json"
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_parameter_metadata(raw)
    return raw


def validate_parameter_metadata(raw):
    """Validate parameter structure and physically meaningful demo ranges."""
    if not isinstance(raw, dict):
        raise ValueError("Parameter file must contain a JSON object.")

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
        raise ValueError(
            "Target low concentration cannot exceed target high concentration."
        )


def unresolved_parameter_citations(path=None):
    """Return parameters with missing or placeholder citations."""
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
    """Calibrate PAH capacity to the configured fasting steady state.

    Uses: endogenous_input = Vmax*C/(Km+C) + k_alt*C.
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

    if k_alt == 0:
        if vmax_eff <= endogenous:
            return np.inf
        return endogenous * km / (vmax_eff - endogenous)

    # Positive root of k_alt*C^2 + (Vmax + k_alt*Km - input)*C
    # - input*Km = 0.
    a = k_alt
    b = vmax_eff + k_alt * km - endogenous
    c = -endogenous * km
    discriminant = b**2 - 4.0 * a * c
    if discriminant < 0:
        raise ValueError("No real steady-state concentration for these parameters.")
    return (-b + np.sqrt(discriminant)) / (2.0 * a)


def simulate(meals, activity_pct, p=None, t_end=24.0, dt=0.05):
    """Simulate blood Phe over time using an illustrative one-compartment model.

    Args:
        meals: Iterable of (time_h, phe_mg) pairs.
        activity_pct: Illustrative residual PAH activity, from 0 to 100.
        p: Optional parameter dictionary; defaults to params.json values.
        t_end: Simulation duration in hours.
        dt: Regular output interval in hours.

    Returns:
        DataFrame with t_h, concentrations, gut_mg, and eliminated_mg.
    """
    p = p or load_params()

    if not np.isfinite(activity_pct) or not 0 <= activity_pct <= 100:
        raise ValueError("activity_pct must be between 0 and 100.")
    if (
        not np.isfinite(t_end)
        or not np.isfinite(dt)
        or t_end <= 0
        or dt <= 0
    ):
        raise ValueError("t_end and dt must be finite and positive.")

    normalized_meals = []
    for meal in meals:
        if len(meal) != 2:
            raise ValueError("Each meal must contain (time_h, phe_mg).")
        time_h, phe_mg = float(meal[0]), float(meal[1])
        if (
            not np.isfinite(time_h)
            or not np.isfinite(phe_mg)
            or time_h < 0
            or time_h > t_end
            or phe_mg < 0
        ):
            raise ValueError("Meals must have valid times and non-negative Phe.")
        normalized_meals.append((time_h, phe_mg))

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
        gut_mg, body_mg, _eliminated_mg = state
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

    # State variables: gut Phe (mg), body-pool Phe (mg), cumulative eliminated Phe (mg).
    state = np.array([0.0, starting_concentration * volume_l, 0.0], dtype=float)

    meals_by_time = {}
    for time_h, phe_mg in normalized_meals:
        meals_by_time[time_h] = meals_by_time.get(time_h, 0.0) + phe_mg

    event_times = sorted(set([0.0, float(t_end), *meals_by_time.keys()]))

    # Round the regular grid to suppress floating-point near-duplicate timestamps.
    regular_times = np.round(np.arange(0.0, t_end, dt), 10)
    output_grid = sorted(
        set([0.0, float(t_end), *regular_times.tolist(), *event_times])
    )

    output_rows = []
    for index, start in enumerate(event_times):
        # Apply any meal at this time before recording the timestamp.
        if start in meals_by_time:
            state[0] += bioavailability * meals_by_time[start]

        output_rows.append((start, state.copy()))

        if index == len(event_times) - 1:
            break

        end = event_times[index + 1]
        if end <= start:
            continue

        interior_times = [t for t in output_grid if start < t < end]
        t_eval = np.asarray(interior_times + [end], dtype=float)

        solution = solve_ivp(
            rhs,
            (start, end),
            state,
            t_eval=t_eval,
            method="LSODA",
            rtol=1e-8,
            atol=1e-8,
        )
        if not solution.success:
            raise RuntimeError(f"Simulation failed: {solution.message}")

        # Do not append the interval endpoint here. The next event-loop pass
        # appends it exactly once, after applying any meal scheduled then.
        for time_h, state_row in zip(solution.t[:-1], solution.y.T[:-1]):
            output_rows.append((float(time_h), state_row.copy()))

        state = solution.y[:, -1].copy()

    output_rows.sort(key=lambda item: item[0])
    times = np.asarray([item[0] for item in output_rows], dtype=float)
    if len(times) == 0 or np.any(np.diff(times) <= 0):
        raise RuntimeError("Simulation output times are not strictly increasing.")

    states = np.vstack([item[1] for item in output_rows])
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
    """Estimate model residual activity from proposed tolerance inputs.

    Calibration helper only. This is not a clinical recommendation.
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
    if vmax_normal <= 0:
        raise ValueError("Normal PAH capacity must be positive.")

    activity_pct = 100.0 * vmax_eff / vmax_normal
    if not 0 <= activity_pct <= 100:
        raise ValueError(
            "Tolerance implies residual activity outside the model's 0–100% range."
        )
    return activity_pct
