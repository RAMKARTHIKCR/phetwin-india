# PheTwin India

This repository contains an educational, one-compartment phenylalanine model
and a Streamlit demonstration. It is an illustrative research prototype, not a
clinical tool, and has not been clinically validated.

## Model assumptions and limitations

- The parameter values in `model/params.json` are explicitly illustrative;
  entries marked `TO_FILL` still require cited scientific sources.
- The model uses a single body compartment, first-order gut absorption,
  Michaelis–Menten PAH elimination, and a linear alternative-clearance term.
- Reference `Vmax` is calibrated to the configured fasting concentration using
  the complete steady-state equation, including alternative clearance.
- `activity_from_tolerance()` is a calibration helper only. It accepts a
  tolerance estimate and target concentration as model inputs and rejects
  inferred activities outside 0–100%; it does not establish a patient's
  phenotype, dietary prescription, or treatment target.
- Food values and meal inputs remain illustrative where the database identifies
  assumptions. No parameter source or clinical conclusion should be inferred
  from the demo.

Run the tests with `python -m pytest -q` from the project root.

For a browser-level check, follow [the manual smoke-test checklist](docs/manual_smoke_test.md).
