
"""Food portion calculations for PheTwin India."""

from database.db import get_all_foods


def calculate_phe(food, portion_grams):
    """Calculate the estimated Phe contribution of a food portion."""
    if portion_grams < 0:
        raise ValueError("Portion size cannot be negative.")

    phe_per_100g = float(food["phe_mg_per_100g"])
    estimated_phe_mg = phe_per_100g * portion_grams / 100

    return {
        "food_name": food["name_en"],
        "portion_grams": float(portion_grams),
        "phe_mg": estimated_phe_mg,
        "is_assumed": int(food["is_assumed"]),
        "source": food["source"],
        "source_ref": food["source_ref"],
    }


def calculate_meal_phe(items):
    """Calculate total estimated Phe for a list of food portions."""
    results = []
    total_phe_mg = 0.0

    for item in items:
        result = calculate_phe(item["food"], item["portion_grams"])
        results.append(result)
        total_phe_mg += result["phe_mg"]

    return {
        "items": results,
        "total_phe_mg": total_phe_mg,
        "contains_assumptions": any(
            result["is_assumed"] == 1 for result in results
        ),
    }


def search_food_options(query):
    """Search foods available in the database."""
    if not query.strip():
        return get_all_foods()

    foods = get_all_foods()
    mask = foods["name_en"].str.contains(query, case=False, na=False, regex=False)

    if "name_ta" in foods.columns:
        mask |= foods["name_ta"].str.contains(
            query, case=False, na=False, regex=False
        )

    return foods[mask].reset_index(drop=True)
