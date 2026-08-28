"""
Loads the Cookie Cats A/B test dataset into SQLite and exposes SQL-based
aggregation queries (group-level conversion/retention counts) that feed
the stats engine.

Dataset: mobile game A/B test on gate placement (level 30 vs level 40).
Columns: userid, version (gate_30/gate_40), sum_gamerounds, retention_1, retention_7
Get it from Kaggle: "Cookie Cats A/B Testing" by mursideyarkin, place the
CSV at data/cookie_cats.csv before running this.
"""
import sqlite3
import csv
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ab_test.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "cookie_cats.csv")


def build_db(csv_path: str = CSV_PATH, db_path: str = DB_PATH):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Expected dataset at {csv_path}. Download 'Cookie Cats A/B Testing' "
            "from Kaggle and place cookie_cats.csv there."
        )

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS plays")
    cur.execute("""
        CREATE TABLE plays (
            userid INTEGER PRIMARY KEY,
            version TEXT NOT NULL,
            sum_gamerounds INTEGER NOT NULL,
            retention_1 INTEGER NOT NULL,
            retention_7 INTEGER NOT NULL
        )
    """)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                int(row["userid"]),
                row["version"],
                int(row["sum_gamerounds"]),
                1 if row["retention_1"] in ("True", "1", "TRUE") else 0,
                1 if row["retention_7"] in ("True", "1", "TRUE") else 0,
            )
            for row in reader
        ]

    cur.executemany("INSERT INTO plays VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()
    print(f"Loaded {len(rows)} rows into {db_path}")


def get_conversion_summary(metric: str, db_path: str = DB_PATH):
    """
    metric: 'retention_1' or 'retention_7'
    Returns per-group (control/variant) conversion counts via SQL aggregation —
    this is the SQL layer feeding the stats engine, not just pandas.
    """
    if metric not in ("retention_1", "retention_7"):
        raise ValueError("metric must be retention_1 or retention_7")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT version,
               COUNT(*) AS n,
               SUM({metric}) AS converted
        FROM plays
        GROUP BY version
    """)
    rows = {r[0]: {"n": r[1], "converted": r[2]} for r in cur.fetchall()}
    conn.close()
    return rows


def get_gamerounds_by_group(db_path: str = DB_PATH):
    """Returns sum_gamerounds as two lists (gate_30, gate_40) for the t-test."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT version, sum_gamerounds FROM plays")
    a, b = [], []
    for version, rounds in cur.fetchall():
        (a if version == "gate_30" else b).append(rounds)
    conn.close()
    return a, b


if __name__ == "__main__":
    build_db()
    print(get_conversion_summary("retention_1"))
