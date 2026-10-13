
"""Core tests for the educational PheTwin India model."""

import numpy as np
import pytest

from model.model import (
    load_params,
    mgl_to_mgdl,
    mgl_to_umol,
    simulate,
)


def test_parameter_file_loads():
    params = load_params()
    assert params["body_weight_kg"] > 0
    assert params["vd_l_per_kg"] > 0


def test_concentration_unit_conversions():
    assert mgl_to_mgdl(10.0) == pytest.approx(1.0)
    assert mgl_to_umol(165.19) == pytest.approx(1000.0)


def test_no_meal_curve_stays_at_steady_state():
    """At 100% reference activity, no-meal concentration should be stable."""
    result = simulate([], activity_pct=100, t_end=6, dt=0.1)

    concentrations = result["conc_mg_l"].to_numpy()
    assert np.all(np.isfinite(concentrations))
    assert np.allclose(concentrations, concentrations[0], rtol=1e-5, atol=1e-5)


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
