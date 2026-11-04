
"""Core tests for the educational PheTwin India model."""

import numpy as np
import pytest

from model.model import (
    activity_from_tolerance,
    calibrate_vmax,
    load_params,
    load_parameter_metadata,
    mgl_to_mgdl,
    mgl_to_umol,
    simulate,
    steady_state_conc,
    target_range_metadata,
    validate_parameter_metadata,
    unresolved_parameter_citations,
)

from model.sensitivity import run_sensitivity
from database.planner import calculate_phe, calculate_meal_phe


def test_parameter_file_loads():
    params = load_params()
    assert params["body_weight_kg"] > 0
    assert params["vd_l_per_kg"] > 0


def test_parameter_metadata_has_citations_and_flags_placeholders():
    metadata = load_parameter_metadata()

    parameters = {
        key: item for key, item in metadata.items() if not key.startswith("_")
    }

    for key, item in parameters.items():
        assert "value" in item, f"Missing value for {key}"
        assert isinstance(item["value"], (int, float))
        assert "citation" in item
        assert item["citation"].strip(), f"Missing citation for {key}"

    assert all(
        str(item.get("citation", "")).strip()
        for item in parameters.values()
    )

    # Only the two clinical target references remain unresolved.
    assert unresolved_parameter_citations() == [
        "target_low_umol_l",
        "target_high_umol_l",
    ]

    assert "context" in metadata["target_low_umol_l"]
    assert "context" in metadata["target_high_umol_l"]


def test_parameter_metadata_rejects_missing_required_entry():
    metadata = load_parameter_metadata()
    metadata.pop("ka_per_h")

    with pytest.raises(ValueError, match="missing required entries"):
        validate_parameter_metadata(metadata)


@pytest.mark.parametrize(
    "parameter, value",
    [
        ("bioavailability", 1.1),
        ("ka_per_h", 0),
        ("body_weight_kg", -1),
    ],
)
def test_parameter_metadata_rejects_invalid_ranges(parameter, value):
    metadata = load_parameter_metadata()
    metadata[parameter]["value"] = value

    with pytest.raises(ValueError):
        validate_parameter_metadata(metadata)


def test_parameter_metadata_rejects_empty_citation():
    metadata = load_parameter_metadata()
    metadata["km_mg_per_l"]["citation"] = ""

    with pytest.raises(ValueError, match="citation field"):
        validate_parameter_metadata(metadata)


def test_target_range_metadata_preserves_context_notes():
    target = target_range_metadata()

    assert target["low"]["value"] == 120
    assert target["high"]["value"] == 360
    assert "age" in target["low"]["context"]
    assert "pregnancy" in target["high"]["context"]


def test_concentration_unit_conversions():
    assert mgl_to_mgdl(10.0) == pytest.approx(1.0)
    assert mgl_to_umol(165.19) == pytest.approx(1000.0)


def test_no_meal_curve_stays_at_steady_state():
    """At 100% reference activity, no-meal concentration should be stable."""
    result = simulate([], activity_pct=100, t_end=6, dt=0.1)

    concentrations = result["conc_mg_l"].to_numpy()

    assert np.all(np.isfinite(concentrations))
    assert np.allclose(
        concentrations,
        concentrations[0],
        rtol=1e-5,
        atol=1e-5,
    )


def test_calibration_matches_full_model_steady_state():
    params = load_params()

    vmax = calibrate_vmax(
        params["endogenous_input_mg_per_h"],
        params["fasting_c0_mg_per_l"],
        params["km_mg_per_l"],
        params["k_alt_l_per_h"],
    )

    assert steady_state_conc(vmax, params) == pytest.approx(
        params["fasting_c0_mg_per_l"]
    )


def test_activity_from_tolerance_has_valid_range():
    activity = activity_from_tolerance(0, 120)

    assert 0 <= activity <= 100


@pytest.mark.parametrize(
    "tolerance, target",
    [
        (-1, 120),
        (0, 0),
        (1500, 120),
    ],
)
def test_activity_from_tolerance_rejects_invalid_or_unachievable_inputs(
    tolerance, target
):
    with pytest.raises(ValueError):
        activity_from_tolerance(tolerance, target)


def test_meals_produce_finite_curve():
    meals = [(8, 400), (13, 600), (20, 500)]
    result = simulate(meals, activity_pct=10)

    assert len(result) > 0
    assert np.all(np.isfinite(result["conc_mg_l"]))
    assert (result["gut_mg"] >= -1e-8).all()
    assert (result["eliminated_mg"] >= -1e-8).all()


def test_mass_balance_with_meals():
    params = load_params()
    meals = [(8, 400), (13, 600), (20, 500)]
    result = simulate(meals, activity_pct=10, p=params)

    volume_l = params["body_weight_kg"] * params["vd_l_per_kg"]
    initial_body_mg = result["conc_mg_l"].iloc[0] * volume_l
    final_body_mg = result["conc_mg_l"].iloc[-1] * volume_l

    expected_input_mg = (
        params["endogenous_input_mg_per_h"] * 24
        + params["bioavailability"] * sum(amount for _, amount in meals)
    )

    accounted_mg = (
        final_body_mg
        - initial_body_mg
        + result["gut_mg"].iloc[-1]
        + result["eliminated_mg"].iloc[-1]
    )

    relative_error = abs(accounted_mg - expected_input_mg) / expected_input_mg

    assert relative_error < 0.01


def test_invalid_activity_is_rejected():
    with pytest.raises(ValueError):
        simulate([], activity_pct=150)


def test_sensitivity_analysis_returns_finite_results():
    baseline, results = run_sensitivity()

    assert np.isfinite(baseline)
    assert len(results) == 6
    assert results["peak_swing_umol_l"].notna().all()
    assert np.isfinite(results["peak_swing_umol_l"]).all()
    assert (results["peak_swing_umol_l"] >= 0).all()


@pytest.fixture
def sample_food():
    return {
        "name_en": "Test food",
        "phe_mg_per_100g": 500.0,
        "is_assumed": 0,
        "source": "Test source",
        "source_ref": "TEST001",
    }


def test_calculate_phe_for_100g(sample_food):
    result = calculate_phe(sample_food, 100)

    assert result["phe_mg"] == pytest.approx(500.0)
    assert result["food_name"] == "Test food"


def test_calculate_phe_for_50g(sample_food):
    result = calculate_phe(sample_food, 50)

    assert result["phe_mg"] == pytest.approx(250.0)


def test_calculate_phe_rejects_negative_portion(sample_food):
    with pytest.raises(ValueError):
        calculate_phe(sample_food, -10)


def test_calculate_meal_phe(sample_food):
    result = calculate_meal_phe([
        {"food": sample_food, "portion_grams": 50},
        {"food": sample_food, "portion_grams": 100},
    ])

    assert result["total_phe_mg"] == pytest.approx(750.0)
    assert result["contains_assumptions"] is False


def test_meal_flags_assumed_food(sample_food):
    sample_food["is_assumed"] = 1

    result = calculate_meal_phe([
        {"food": sample_food, "portion_grams": 100},
    ])

    assert result["contains_assumptions"] is True


def test_calibration_includes_alternative_clearance():
    params = load_params()

    vmax = calibrate_vmax(
        params["endogenous_input_mg_per_h"],
        params["fasting_c0_mg_per_l"],
        params["km_mg_per_l"],
        params["k_alt_l_per_h"],
    )

    calculated = steady_state_conc(vmax, params)

    assert calculated == pytest.approx(
        params["fasting_c0_mg_per_l"],
        rel=1e-8,
    )


def test_activity_from_tolerance_returns_valid_percentage():
    result = activity_from_tolerance(
        tolerance_mg_per_day=500,
        c_target_umol=360,
    )

    assert 0 <= result <= 100


def test_simulation_mass_balance():
    p = load_params()
    meals = [(8, 400), (13, 600)]
    activity = 50
    duration = 24

    result = simulate(
        meals=meals,
        activity_pct=activity,
        p=p,
        t_end=duration,
        dt=0.05,
    )

    volume = p["body_weight_kg"] * p["vd_l_per_kg"]

    vmax = calibrate_vmax(
        p["endogenous_input_mg_per_h"],
        p["fasting_c0_mg_per_l"],
        p["km_mg_per_l"],
        p["k_alt_l_per_h"],
    ) * activity / 100

    initial_body = steady_state_conc(vmax, p) * volume
    endogenous_input = p["endogenous_input_mg_per_h"] * duration
    meal_input = sum(amount for _, amount in meals) * p["bioavailability"]

    total_input = initial_body + endogenous_input + meal_input

    total_accounted = (
        result["gut_mg"].iloc[-1]
        + result["conc_mg_l"].iloc[-1] * volume
        + result["eliminated_mg"].iloc[-1]
    )

    assert abs(total_input - total_accounted) / total_input < 1e-5
