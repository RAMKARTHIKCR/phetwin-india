# Manual smoke-test checklist

Run the app with `streamlit run app.py` from the project root and open the
local Streamlit URL.

## Food calculator

- Confirm the page loads with the educational-use warning.
- Select a food and calculate a positive portion.
- Confirm the result shows portion size, estimated Phe, source, and source reference.
- Try a zero or negative portion and confirm the app reports an error without stopping.

## Meal builder

- Create a meal and add at least one food.
- Confirm the meal table and total estimated Phe update.
- Remove an item and clear the meal.
- Confirm assumed food values display an assumption warning.

## Simulation

- Confirm the simulation section shows the unresolved-parameter warning.
- Run the default illustrative simulation.
- Confirm a chart, summary metrics, data table, and CSV download appear.
- Try meal times beyond the selected duration and confirm validation prevents the run.

## Interpretation boundary

The app must continue to label outputs as illustrative. No result should be
presented as a patient measurement, dietary prescription, treatment setting, or
clinical validation result.
