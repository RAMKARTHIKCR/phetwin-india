
"""One-at-a-time sensitivity analysis for PheTwin India.

Uses illustrative parameters and meal inputs. Results are not clinical predictions.
Run from the project root:
    python -m model.sensitivity
"""

import copy

import pandas as pd

from model.model import load_params, simulate


# Illustrative meal inputs only: (time in hours, Phe in mg).
MEALS = [(8, 400), (13, 600), (20, 500)]

# Illustrative residual PAH activity, not a clinical phenotype preset.
ACTIVITY_PCT = 10.0

# Parameters to vary individually by +/-20%.
PARAMETERS = [
    "km_mg_per_l",
    "vd_l_per_kg",
    "endogenous_input_mg_per_h",
    "k_alt_l_per_h",
    "ka_per_h",
    "bioavailability",
]


def peak_concentration(params):
    """Return the maximum simulated Phe concentration in micromol/L."""
    result = simulate(MEALS, ACTIVITY_PCT, p=params)
    return float(result["conc_umol_l"].max())


def run_sensitivity(change=0.20):
    """Vary one parameter at a time and rank its effect on peak Phe."""
    if not 0 < change < 1:
        raise ValueError("change must be greater than 0 and less than 1.")

    baseline_params = load_params()
    baseline_peak = peak_concentration(baseline_params)
    rows = []

    for name in PARAMETERS:
        low_params = copy.deepcopy(baseline_params)
        high_params = copy.deepcopy(baseline_params)

        original_value = baseline_params[name]
        
        low_value = original_value * (1 - change)
        high_value = original_value * (1 + change)

        # Respect the physically valid range of bioavailability.
        if name == "bioavailability":
            low_value = max(0.0, low_value)
            high_value = min(1.0, high_value)

        low_params[name] = low_value
        high_params[name] = high_value

        low_peak = peak_concentration(low_params)
        high_peak = peak_concentration(high_params)


        rows.append(
            {
                "parameter": name,
                "baseline_value": original_value,
                "peak_minus_20_pct_umol_l": low_peak,
                "peak_plus_20_pct_umol_l": high_peak,
                "peak_swing_umol_l": abs(high_peak - low_peak),
            }
        )

    table = pd.DataFrame(rows).sort_values(
        "peak_swing_umol_l", ascending=False
    )

    return baseline_peak, table


if __name__ == "__main__":
    baseline, results = run_sensitivity()

    print("PHETWIN INDIA — ILLUSTRATIVE SENSITIVITY ANALYSIS")
    print("Not validated for clinical use.")
    print(f"Baseline peak: {baseline:.2f} micromol/L")
    print()
    print(results.round(2).to_string(index=False))
