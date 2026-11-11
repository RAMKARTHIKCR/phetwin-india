
"""Validate IFCT expansion staging rows without touching the production CSV."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STAGING_PATH = ROOT / "data" / "foods_expansion_staging.csv"

REQUIRED_COLUMNS = [
    "name_en",
    "protein_g_per_100g",
    "phe_mg_per_100g",
    "source",
    "source_ref",
    "ifct_code",
    "table1_page",
    "table8_page",
    "table1_protein_g_per_100g",
    "table8_phe_g_per_100g_protein",
    "verification_status",
    "permission_status",
]

NUTRIENT_FIELDS = [
    "protein_g_per_100g",
    "phe_mg_per_100g",
    "table1_protein_g_per_100g",
    "table8_phe_g_per_100g_protein",
]

REFERENCE_FIELDS = [
    "source_ref",
    "table1_page",
    "table8_page",
]

VERIFIED_STATUSES = {
    "VERIFIED",
    "SOURCE_VALUES_VERIFIED_DERIVED_PHE",
}


def validate_staging() -> int:
    print("Starting IFCT staging validation...")

    if not STAGING_PATH.exists():
        print(f"ERROR: Staging file not found: {STAGING_PATH}")
        return 1

    df = pd.read_csv(STAGING_PATH, keep_default_na=False)
    errors: list[str] = []

    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        print(f"ERROR: Missing columns: {missing}")
        return 1

    if df.empty:
        print("ERROR: Staging CSV contains no rows.")
        return 1

    if df["name_en"].duplicated().any():
        errors.append("Duplicate staging food names")

    if df["ifct_code"].duplicated().any():
        errors.append("Duplicate staging IFCT codes")

    for row_number, row in df.iterrows():
        row_label = row_number + 2
        status = str(row["verification_status"]).strip()
        permission = str(row["permission_status"]).strip()

        if not str(row["name_en"]).strip():
            errors.append(f"Row {row_label}: missing English food name")

        if status not in VERIFIED_STATUSES:
            if any(str(row[field]).strip() for field in NUTRIENT_FIELDS):
                errors.append(
                    f"Row {row_label}: unverified row contains nutrient values"
                )

            if any(str(row[field]).strip() for field in REFERENCE_FIELDS):
                errors.append(
                    f"Row {row_label}: unverified row contains source references"
                )

        else:
            if any(
                not str(row[field]).strip()
                for field in NUTRIENT_FIELDS + REFERENCE_FIELDS
            ):
                errors.append(
                    f"Row {row_label}: verified row is incomplete"
                )

            # Check that nutrient fields contain valid numbers.
            numeric_values = {}
            for field in NUTRIENT_FIELDS:
                try:
                    numeric_values[field] = float(row[field])
                except (TypeError, ValueError):
                    errors.append(
                        f"Row {row_label}: {field} must be numeric"
                    )

            # Check the derived Phe calculation:
            # protein × Phe per 100 g protein × 10 = Phe mg per 100 g food.
            if len(numeric_values) == len(NUTRIENT_FIELDS):
                expected_phe = (
                    numeric_values["table1_protein_g_per_100g"]
                    * numeric_values["table8_phe_g_per_100g_protein"]
                    * 10
                )
                actual_phe = numeric_values["phe_mg_per_100g"]

                if abs(expected_phe - actual_phe) > 0.02:
                    errors.append(
                        f"Row {row_label}: derived Phe mismatch "
                        f"(expected approximately {expected_phe:.2f}, "
                        f"found {actual_phe:.2f})"
                    )

                if numeric_values["protein_g_per_100g"] <= 0:
                    errors.append(
                        f"Row {row_label}: protein must be greater than zero"
                    )

                if numeric_values["phe_mg_per_100g"] < 0:
                    errors.append(
                        f"Row {row_label}: Phe cannot be negative"
                    )

        if status == "SOURCE_VALUES_VERIFIED_DERIVED_PHE":
            if permission != "PERMISSION_REVIEW_REQUIRED":
                errors.append(
                    f"Row {row_label}: expected permission status "
                    "'PERMISSION_REVIEW_REQUIRED'"
                )

    print("\nIFCT EXPANSION STAGING VALIDATION")
    print("--------------------------------")
    print(f"Rows checked: {len(df)}")
    print(f"Errors found: {len(errors)}")

    if errors:
        print("\nVALIDATION ERRORS:")
        for error in errors:
            print(f"- {error}")

        print("\nResult: FAILED")
        print("Production foods_final.csv was not modified.")
        return 1

    print("\nResult: STRUCTURAL AND CALCULATION CHECKS PASSED.")
    print(
        "Important: this script does not independently authenticate "
        "IFCT source values or page references."
    )
    print(
        "Permission review is still required before production integration."
    )
    print("Production foods_final.csv was not modified.")

    return 0


if __name__ == "__main__":
    raise SystemExit(validate_staging())
