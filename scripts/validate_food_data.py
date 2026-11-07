
import pandas as pd
from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "foods_final.csv"
OUTPUT_PATH = ROOT / "data" / "food_validation_report.csv"

# IFCT source reference checks
REQUIRED_COLUMNS = [
    "name_en",
    "protein_g_per_100g",
    "phe_mg_per_100g",
    "source",
    "source_ref",
    "is_assumed",
]

def validate_food_data():
    df = pd.read_csv(CSV_PATH)

    errors = []
    warnings = []

    # 1. Check required columns
    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing CSV columns: {missing_columns}"
        )

    # 2. Check missing and duplicate food names
    for index, row in df.iterrows():
        food = row["name_en"]
        row_number = index + 2

        if pd.isna(food) or not str(food).strip():
            errors.append({
                "row": row_number,
                "food": "",
                "issue": "Missing English food name",
            })

    duplicates = df[
        df["name_en"].duplicated(keep=False)
    ]

    for _, row in duplicates.iterrows():
        errors.append({
            "row": "",
            "food": row["name_en"],
            "issue": "Duplicate English food name",
        })

    # 3. Validate numeric values
    for index, row in df.iterrows():
        food = row["name_en"]
        row_number = index + 2

        for column in [
            "protein_g_per_100g",
            "phe_mg_per_100g",
        ]:
            value = pd.to_numeric(
                row[column], errors="coerce"
            )

            if pd.isna(value):
                errors.append({
                    "row": row_number,
                    "food": food,
                    "issue": f"Invalid numeric value: {column}",
                })
            elif value < 0:
                errors.append({
                    "row": row_number,
                    "food": food,
                    "issue": f"Negative value: {column}",
                })

        protein = pd.to_numeric(
            row["protein_g_per_100g"],
            errors="coerce",
        )

        phe = pd.to_numeric(
            row["phe_mg_per_100g"],
            errors="coerce",
        )

        # 4. Calculate implied Phe composition
        if (
            pd.notna(protein)
            and pd.notna(phe)
            and protein > 0
        ):
            implied_phe = phe / (protein * 10)

            if not 0 <= implied_phe <= 10:
                warnings.append({
                    "row": row_number,
                    "food": food,
                    "issue": (
                        "Unusual implied Phe composition: "
                        f"{implied_phe:.3f} g/100 g protein"
                    ),
                })

    # 5. Check source references
    for index, row in df.iterrows():
        food = row["name_en"]
        source = str(row["source"])
        source_ref = str(row["source_ref"])

        if "IFCT 2017" not in source:
            warnings.append({
                "row": index + 2,
                "food": food,
                "issue": "Source is not identified as IFCT 2017",
            })

        if "Table 1" not in source_ref or "Table 8" not in source_ref:
            warnings.append({
                "row": index + 2,
                "food": food,
                "issue": "Missing Table 1 or Table 8 reference",
            })

    # 6. Check assumption flags
    for index, row in df.iterrows():
        flag = row["is_assumed"]

        if flag not in [0, 1]:
            errors.append({
                "row": index + 2,
                "food": row["name_en"],
                "issue": "Invalid is_assumed flag",
            })

    # 7. Save report
    report_rows = []

    for item in errors:
        report_rows.append({
            "status": "ERROR",
            **item,
        })

    for item in warnings:
        report_rows.append({
            "status": "WARNING",
            **item,
        })

    report = pd.DataFrame(
        report_rows,
        columns=["status", "row", "food", "issue"],
    )

    report.to_csv(OUTPUT_PATH, index=False)

    # 8. Print summary
    print("\n===================================")
    print(" PHETWIN INDIA FOOD DATA VALIDATION")
    print("===================================")

    print(f"Total food records: {len(df)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    print("\nImplied Phe composition:")
    ratios = (
        df["phe_mg_per_100g"]
        / (df["protein_g_per_100g"] * 10)
    )

    print(f"Minimum: {ratios.min():.3f} g/100 g protein")
    print(f"Maximum: {ratios.max():.3f} g/100 g protein")

    print(f"\nReport saved to: {OUTPUT_PATH}")

    if errors:
        print("\nERRORS:")
        for item in errors:
            print(item)

    if warnings:
        print("\nWARNINGS:")
        for item in warnings:
            print(item)

    if not errors and not warnings:
        print("\nAll structural checks passed!")


if __name__ == "__main__":
    validate_food_data()
