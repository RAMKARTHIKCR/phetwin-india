"""SQLite database utilities for PheTwin India."""

import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "data" / "foods_final.csv"
DEFAULT_DB = PROJECT_ROOT / "data" / "phetwin.db"


def create_connection(db_path=DEFAULT_DB):
    """Create the database directory and return a SQLite connection."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path=DEFAULT_DB):
    """Create the foods table if it does not already exist."""
    with create_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_en TEXT NOT NULL,
                name_ta TEXT,
                category TEXT NOT NULL,
                state TEXT NOT NULL,
                protein_g_per_100g REAL NOT NULL,
                phe_mg_per_100g REAL NOT NULL,
                is_assumed INTEGER NOT NULL CHECK (is_assumed IN (0, 1)),
                source TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                measure_label TEXT,
                measure_grams REAL
            )
            """
        )


def load_foods_from_csv(csv_path=DEFAULT_CSV, db_path=DEFAULT_DB):
    """Load the CSV into SQLite, replacing the existing food records."""
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Food CSV not found: {csv_path}")

    foods = pd.read_csv(csv_path)

    required_columns = [
        "name_en",
        "name_ta",
        "category",
        "state",
        "protein_g_per_100g",
        "phe_mg_per_100g",
        "is_assumed",
        "source",
        "source_ref",
        "measure_label",
        "measure_grams",
    ]

    if foods.columns.tolist() != required_columns:
        raise ValueError("The food CSV columns do not match the expected schema.")

    if foods["name_en"].isna().any() or foods["name_en"].str.strip().eq("").any():
        raise ValueError("Every food record must have an English name.")

    if foods["name_en"].duplicated().any():
        raise ValueError("Duplicate English food names were found.")

    with create_connection(db_path) as connection:
        connection.execute("DELETE FROM foods")
        foods.to_sql("foods", connection, if_exists="append", index=False)


def get_all_foods(db_path=DEFAULT_DB):
    """Return all food records as a pandas DataFrame."""
    with create_connection(db_path) as connection:
        return pd.read_sql_query(
            "SELECT * FROM foods ORDER BY name_en",
            connection,
        )


def search_foods(query, db_path=DEFAULT_DB):
    """Search food names in English or Tamil."""
    query = query.strip()

    with create_connection(db_path) as connection:
        return pd.read_sql_query(
            """
            SELECT *
            FROM foods
            WHERE name_en LIKE ? OR name_ta LIKE ?
            ORDER BY name_en
            """,
            connection,
            params=(f"%{query}%", f"%{query}%"),
        )
