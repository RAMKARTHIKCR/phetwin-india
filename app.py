
"""PheTwin India — educational PKU food and meal planning tool."""

import streamlit as st

from database.db import get_all_foods
from database.planner import calculate_phe


st.set_page_config(
    page_title="PheTwin India",
    page_icon="🧬",
    layout="wide",
)

st.title("🧬 PheTwin India")
st.caption("An educational phenylalanine (Phe) food-data and simulation tool")

st.warning(
    "**Educational use only.** This prototype is not a medical device and "
    "is not validated for clinical decisions. It does not provide a safe "
    "dietary allowance or individualized PKU treatment advice. Follow your "
    "metabolic care team's guidance."
)

# Initialise session-based meal storage.
if "meals" not in st.session_state:
    st.session_state.meals = {"My Meal": []}

if "active_meal" not in st.session_state:
    st.session_state.active_meal = "My Meal"

if st.session_state.active_meal not in st.session_state.meals:
    st.session_state.active_meal = next(iter(st.session_state.meals))


@st.cache_data
def load_food_data():
    """Load food records from SQLite."""
    return get_all_foods()


try:
    foods = load_food_data()
except Exception as exc:
    st.error(f"Could not load the food database: {exc}")
    st.stop()

if foods.empty:
    st.error("No food records found. Load the food CSV into SQLite first.")
    st.stop()

# Make missing Tamil names safe to search.
foods["name_ta"] = foods["name_ta"].fillna("")

# ---------------------------------------------------------
# Original single-food calculator
# ---------------------------------------------------------

st.header("1. Indian Food Phe Calculator")
st.write("Calculate the estimated Phe contribution of one food portion.")

search = st.text_input(
    "Search foods in English or Tamil",
    placeholder="Example: rice, wheat, lentil",
    key="single_food_search",
)

single_mask = (
    foods["name_en"].str.contains(
        search.strip(), case=False, na=False, regex=False
    )
    | foods["name_ta"].str.contains(
        search.strip(), case=False, na=False, regex=False
    )
)

single_filtered = foods[single_mask].reset_index(drop=True)

if single_filtered.empty:
    st.info("No matching foods found. Try another search term.")
else:
    single_name = st.selectbox(
        "Select a food",
        single_filtered["name_en"].tolist(),
        key="single_food_select",
    )

    single_food = single_filtered.loc[
        single_filtered["name_en"] == single_name
    ].iloc[0]

    single_portion = st.number_input(
        "Portion size (grams)",
        min_value=0.0,
        max_value=5000.0,
        value=100.0,
        step=10.0,
        key="single_food_portion",
    )

    if st.button("Calculate Phe", type="primary", key="single_calculate"):
        try:
            result = calculate_phe(single_food, single_portion)

            st.subheader("Single-food result")
            col1, col2 = st.columns(2)
            col1.metric("Portion size", f"{result['portion_grams']:.1f} g")
            col2.metric("Estimated Phe", f"{result['phe_mg']:.2f} mg")

            if result["is_assumed"] == 1:
                st.warning(
                    "This food uses an assumed or estimated Phe value. "
                    "Treat the result as an estimate, not a direct measurement."
                )
            else:
                st.info(
                    "This record is not marked as assumed. Its Phe value "
                    "may still be calculated from source data rather than "
                    "measured directly in the food."
                )

            st.write("**Source:**", result["source"])
            st.write("**Source reference:**", result["source_ref"])

        except (ValueError, KeyError, TypeError) as exc:
            st.error(f"Could not calculate the portion: {exc}")

st.divider()

# ---------------------------------------------------------
# Session-based meal builder
# ---------------------------------------------------------

st.header("2. Meal Builder")
st.write(
    "Build several meals, add food portions, and review their estimated "
    "Phe totals. Meals are saved only in this active app session."
)

with st.form("create_meal_form", clear_on_submit=True):
    new_meal_name = st.text_input(
        "Name for a new meal",
        placeholder="Example: Breakfast",
    )
    create_meal_clicked = st.form_submit_button("Create meal")

if create_meal_clicked:
    cleaned_name = new_meal_name.strip()

    if not cleaned_name:
        st.error("Enter a meal name.")
    elif cleaned_name in st.session_state.meals:
        st.error("A meal with that name already exists.")
    else:
        st.session_state.meals[cleaned_name] = []
        st.session_state.active_meal = cleaned_name
        st.rerun()

meal_names = list(st.session_state.meals.keys())

active_index = meal_names.index(st.session_state.active_meal)

active_meal_name = st.selectbox(
    "Choose a meal",
    meal_names,
    index=active_index,
    key="active_meal_selector",
)

st.session_state.active_meal = active_meal_name

# Select and add a food.
meal_search = st.text_input(
    "Search foods to add",
    placeholder="Search in English or Tamil",
    key="meal_food_search",
)

meal_mask = (
    foods["name_en"].str.contains(
        meal_search.strip(), case=False, na=False, regex=False
    )
    | foods["name_ta"].str.contains(
        meal_search.strip(), case=False, na=False, regex=False
    )
)

meal_filtered = foods[meal_mask].reset_index(drop=True)

if meal_filtered.empty:
    st.info("No matching foods found.")
else:
    selected_meal_food_name = st.selectbox(
        "Food to add",
        meal_filtered["name_en"].tolist(),
        key="meal_food_select",
    )

    selected_meal_food = meal_filtered.loc[
        meal_filtered["name_en"] == selected_meal_food_name
    ].iloc[0]

    meal_portion = st.number_input(
        "Food portion (grams)",
        min_value=0.0,
        max_value=5000.0,
        value=100.0,
        step=10.0,
        key="meal_food_portion",
    )

    if st.button("Add food to meal", type="primary"):
        if meal_portion <= 0:
            st.error("Enter a portion greater than zero.")
        else:
            try:
                result = calculate_phe(
                    selected_meal_food,
                    meal_portion,
                )

                st.session_state.meals[active_meal_name].append(result)
                st.success(
                    f"Added {result['food_name']} to {active_meal_name}."
                )
                st.rerun()

            except (ValueError, KeyError, TypeError) as exc:
                st.error(f"Could not add food: {exc}")

# Display the active meal.
st.subheader(f"Meal contents: {active_meal_name}")

meal_items = st.session_state.meals[active_meal_name]

if not meal_items:
    st.info("This meal is empty. Add a food using the form above.")
else:
    display_rows = []

    for index, item in enumerate(meal_items):
        display_rows.append(
            {
                "Item": index + 1,
                "Food": item["food_name"],
                "Portion (g)": round(item["portion_grams"], 2),
                "Estimated Phe (mg)": round(item["phe_mg"], 2),
                "Assumed value": "Yes" if item["is_assumed"] == 1 else "No",
            }
        )

    st.dataframe(
        display_rows,
        use_container_width=True,
        hide_index=True,
    )

    total_phe = sum(item["phe_mg"] for item in meal_items)
    total_portion = sum(item["portion_grams"] for item in meal_items)
    contains_assumptions = any(
        item["is_assumed"] == 1 for item in meal_items
    )

    col1, col2 = st.columns(2)
    col1.metric("Combined portion weight", f"{total_portion:.1f} g")
    col2.metric("Total estimated Phe", f"{total_phe:.2f} mg")

    if contains_assumptions:
        st.warning(
            "At least one food uses an assumed or estimated Phe value. "
            "The meal total is therefore partly assumption-based."
        )
    else:
        st.info(
            "No foods in this meal are marked as assumed. Values may still "
            "be calculated estimates rather than direct measurements."
        )

    with st.expander("View meal sources"):
        for index, item in enumerate(meal_items, start=1):
            st.write(
                f"{index}. **{item['food_name']}** — "
                f"{item['source']} ({item['source_ref']})"
            )

    remove_index = st.selectbox(
        "Select an item to remove",
        options=list(range(len(meal_items))),
        format_func=lambda i: (
            f"{i + 1}. {meal_items[i]['food_name']} "
            f"({meal_items[i]['portion_grams']:.1f} g)"
        ),
        key="remove_meal_item",
    )

    col_remove, col_clear = st.columns(2)

    with col_remove:
        if st.button("Remove selected item"):
            st.session_state.meals[active_meal_name].pop(remove_index)
            st.rerun()

    with col_clear:
        if st.button("Clear this meal"):
            st.session_state.meals[active_meal_name] = []
            st.rerun()

st.divider()

# Overview of meals saved in this session.
st.subheader("Meals saved in this session")

overview = []

for name, items in st.session_state.meals.items():
    overview.append(
        {
            "Meal": name,
            "Food items": len(items),
            "Estimated Phe (mg)": round(
                sum(item["phe_mg"] for item in items), 2
            ),
        }
    )

st.dataframe(overview, use_container_width=True, hide_index=True)

with st.expander("About the food database and estimates"):
    st.write(f"Food records available: **{len(foods)}**")
    st.write(
        "Phe values may be calculated from protein and amino-acid composition. "
        "Raw, cooked, and processed food states must not be treated as "
        "interchangeable."
    )
    st.write(
        "Meal totals are sums of the selected food-record values. They do "
        "not predict an individual's blood phenylalanine response."
    )

st.divider()
st.caption(
    "PheTwin India | Student capstone prototype | "
    "Not intended for diagnosis, treatment, or dietary decisions."
)


# ---------------------------------------------------------
# Blood Phe simulation — educational prototype only
# ---------------------------------------------------------

st.divider()
st.header("3. Blood Phenylalanine Simulation")

st.warning(
    "**Illustrative simulation only.** This model is not clinically validated "
    "and must not be used to predict an individual's actual blood Phe, "
    "adjust treatment, or make dietary decisions. The default parameters "
    "are illustrative and require appropriate sourcing and validation."
)

from model.model import simulate, load_params
import plotly.express as px

st.write(
    "Explore how the current mathematical model responds to illustrative "
    "meal inputs and residual PAH activity. These inputs are not "
    "recommended meal quantities or treatment settings."
)

with st.expander("Model assumptions and limitations", expanded=True):
    st.markdown(
        """
        - The model uses a simplified one-compartment representation.
        - Meal Phe values are model inputs, not measurements of absorbed Phe.
        - Residual PAH activity is an illustrative model control.
        - The output is not validated against patient data.
        - A simulated concentration must not be interpreted as an individual's
          measured blood Phe or a clinical target.
        """
    )

try:
    model_params = load_params()
except Exception as exc:
    st.error(f"Could not load simulation parameters: {exc}")
    st.stop()

with st.form("simulation_form"):
    st.subheader("Simulation settings")

    sim_duration = st.slider(
        "Simulation duration (hours)",
        min_value=6,
        max_value=48,
        value=24,
        step=6,
    )

    sim_dt = st.select_slider(
        "Output time step (hours)",
        options=[0.25, 0.5, 1.0],
        value=0.25,
    )

    activity_pct = st.slider(
        "Illustrative residual PAH activity (%)",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        help="Exploratory model input only; not an individual's measured activity.",
    )

    st.subheader("Illustrative meal inputs")

    meal1_col, meal2_col = st.columns(2)

    with meal1_col:
        meal1_time = st.number_input(
            "Meal 1 time (hours from simulation start)",
            min_value=0.0,
            max_value=48.0,
            value=8.0,
            step=0.5,
        )
        meal1_phe = st.number_input(
            "Meal 1 Phe input (mg)",
            min_value=0.0,
            max_value=10000.0,
            value=400.0,
            step=50.0,
        )

    with meal2_col:
        meal2_time = st.number_input(
            "Meal 2 time (hours from simulation start)",
            min_value=0.0,
            max_value=48.0,
            value=13.0,
            step=0.5,
        )
        meal2_phe = st.number_input(
            "Meal 2 Phe input (mg)",
            min_value=0.0,
            max_value=10000.0,
            value=600.0,
            step=50.0,
        )

    run_simulation = st.form_submit_button("Run illustrative simulation")

if run_simulation:
    if meal1_time > sim_duration or meal2_time > sim_duration:
        st.error("Both meal times must fall within the simulation duration.")
    else:
        try:
            meals = [
                (float(meal1_time), float(meal1_phe)),
                (float(meal2_time), float(meal2_phe)),
            ]

            simulation = simulate(
                meals=meals,
                activity_pct=int(activity_pct),
                p=model_params,
                t_end=float(sim_duration),
                dt=float(sim_dt),
            )

            st.subheader("Simulated concentration over time")

            chart = px.line(
                simulation,
                x="t_h",
                y="conc_umol_l",
                labels={
                    "t_h": "Time (hours)",
                    "conc_umol_l": "Simulated concentration (µmol/L)",
                },
                title="Illustrative blood-Phe model output",
            )

            chart.update_layout(
                xaxis_title="Time (hours)",
                yaxis_title="Simulated concentration (µmol/L)",
            )

            st.plotly_chart(chart, use_container_width=True)

            metric1, metric2, metric3 = st.columns(3)

            metric1.metric(
                "Initial concentration",
                f"{simulation['conc_umol_l'].iloc[0]:.2f} µmol/L",
            )

            metric2.metric(
                "Maximum simulated concentration",
                f"{simulation['conc_umol_l'].max():.2f} µmol/L",
            )

            metric3.metric(
                "Final simulated concentration",
                f"{simulation['conc_umol_l'].iloc[-1]:.2f} µmol/L",
            )

            st.subheader("Simulation data")

            st.dataframe(
                simulation.round(3),
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download simulation results (CSV)",
                data=simulation.to_csv(index=False).encode("utf-8"),
                file_name="phetwin_illustrative_simulation.csv",
                mime="text/csv",
            )

        except Exception as exc:
            st.error(f"Simulation could not be completed: {exc}")
