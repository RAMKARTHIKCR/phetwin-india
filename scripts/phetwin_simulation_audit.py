"""
PheTwin India — additional simulation scenario audit
Run from the project root:
    .venv\Scripts\python.exe phetwin_simulation_audit.py

This diagnostic does not modify project files or model parameters.
It checks numerical output and mass balance for selected illustrative scenarios.
It is not clinical validation.
"""
import sys
from pathlib import Path

import numpy as np

# Ensure imports resolve when this script is run from the project root.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.model import load_params, simulate


def check_case(name, meals, activity_pct=50.0, t_end=24.0, dt=0.25):
    params = load_params()
    result = simulate(
        meals=meals,
        activity_pct=activity_pct,
        p=params,
        t_end=t_end,
        dt=dt,
    )

    required = {
        "t_h", "conc_mg_l", "conc_umol_l", "conc_mg_dl",
        "gut_mg", "eliminated_mg"
    }
    missing = required.difference(result.columns)
    assert not missing, f"{name}: missing output columns: {sorted(missing)}"

    times = result["t_h"].to_numpy(dtype=float)
    assert len(times) >= 2, f"{name}: too few output rows"
    assert np.all(np.isfinite(result[list(required)].to_numpy(dtype=float))), (
        f"{name}: non-finite output detected"
    )
    assert np.all(np.diff(times) > 0), f"{name}: timestamps are not strictly increasing"
    assert np.isclose(times[0], 0.0), f"{name}: output does not start at zero"
    assert np.isclose(times[-1], t_end), f"{name}: output does not end at t_end"

    volume_l = params["body_weight_kg"] * params["vd_l_per_kg"]
    initial_body_mg = result.iloc[0]["conc_mg_l"] * volume_l
    total_meal_input = params["bioavailability"] * sum(phe for _, phe in meals)
    endogenous_input = params["endogenous_input_mg_per_h"] * t_end

    # A meal at t=0 is added to the gut compartment before the first row is
    # recorded. Total meal input is therefore counted once in the balance.
    accounted_initial = initial_body_mg
    accounted_inputs = total_meal_input + endogenous_input
    final_stored = (
        result.iloc[-1]["gut_mg"]
        + result.iloc[-1]["conc_mg_l"] * volume_l
        + result.iloc[-1]["eliminated_mg"]
    )
    mass_error = abs(accounted_initial + accounted_inputs - final_stored)

    assert mass_error < 1e-4, (
        f"{name}: mass-balance discrepancy {mass_error:.6g} mg exceeds 1e-4 mg"
    )

    return {
        "name": name,
        "rows": len(result),
        "peak_umol_l": float(result["conc_umol_l"].max()),
        "mass_error_mg": float(mass_error),
        "duplicate_timestamps": int(len(times) - len(np.unique(times))),
    }


def main():
    cases = [
        ("No meals", [], 50.0, 24.0, 0.25),
        ("One meal", [(8.0, 400.0)], 50.0, 24.0, 0.25),
        ("Multiple meals", [(8.0, 400.0), (13.0, 600.0), (20.0, 500.0)], 50.0, 24.0, 0.25),
        ("Meal at time zero", [(0.0, 250.0)], 50.0, 24.0, 0.25),
        ("Meal at simulation endpoint", [(24.0, 250.0)], 50.0, 24.0, 0.25),
        ("Smaller time step", [(8.0, 400.0), (13.0, 600.0)], 50.0, 24.0, 0.10),
        ("Larger time step", [(8.0, 400.0), (13.0, 600.0)], 50.0, 24.0, 0.50),
        ("Simultaneous meals", [(8.0, 200.0), (8.0, 300.0)], 50.0, 24.0, 0.25),
    ]

    print("PHETWIN INDIA — SIMULATION SCENARIO AUDIT")
    print("-" * 58)
    passed = 0
    for name, meals, activity, duration, step in cases:
        result = check_case(name, meals, activity, duration, step)
        passed += 1
        print(
            f"PASS | {result['name']}: rows={result['rows']}, "
            f"peak={result['peak_umol_l']:.3f} µmol/L, "
            f"mass error={result['mass_error_mg']:.3e} mg, "
            f"duplicate timestamps={result['duplicate_timestamps']}"
        )

    print("-" * 58)
    print(f"RESULT: {passed}/{len(cases)} scenarios passed.")
    print("Note: numerical consistency checks only; not clinical validation.")


if __name__ == "__main__":
    main()
