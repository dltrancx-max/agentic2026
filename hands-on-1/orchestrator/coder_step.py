"""The NORMALIZE phase — the 'Coder Agent' in the architecture.

Reads the legacy CSV the worker exported and produces:
  * output/manifests_23ai.csv         (rows in the new schema)
  * output/reconciliation.txt         (row counts + total — proof the data
                                       came through clean)

This is plain Python, not an LLM call. It's labelled 'Coder' in the
architecture because in a real run the Coder Agent would *write* this
transformer based on the legacy and target schemas. Here we ship the
already-written transformer so the practical stays focused on the agent loop.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from config import (
    NORMALIZED_FILE, NUMERIC_COLUMNS, RECONCILIATION_FILE, SCHEMA_MAP,
)

log = logging.getLogger("orchestrator.coder")


_MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def _dd_mon_yy_to_iso(s: str) -> str:
    """'15-JUL-25' -> '2025-07-15'. Treats two-digit year >= 70 as 19xx."""
    day, mon, yy = s.split("-")
    yy_int = int(yy)
    year = 1900 + yy_int if yy_int >= 70 else 2000 + yy_int
    return f"{year:04d}-{_MONTHS[mon.upper()]}-{int(day):02d}"


def normalize(
    legacy_csv: Path,
    *,
    out_csv: Path = NORMALIZED_FILE,
    out_report: Path = RECONCILIATION_FILE,
) -> dict:
    """Transform legacy CSV -> 23ai CSV and write a reconciliation report.

    Returns a dict the orchestrator can log and put into the checkpoint:
        {
          "rows_in": N,
          "rows_out": N,
          "amount_in_total": ...,
          "amount_out_total": ...,
          "normalized_file": Path,
          "report_file": Path,
        }
    """
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with legacy_csv.open(encoding="utf-8", newline="") as f:
        legacy_rows = list(csv.DictReader(f))

    new_cols = [SCHEMA_MAP[c] for c in legacy_rows[0].keys()] if legacy_rows else []
    new_rows: list[dict] = []
    for r in legacy_rows:
        new = {SCHEMA_MAP[k]: v for k, v in r.items()}
        new["ship_date"] = _dd_mon_yy_to_iso(new["ship_date"])
        for col in NUMERIC_COLUMNS:
            if col in new and new[col] != "":
                new[col] = float(new[col]) if "." in new[col] else int(new[col])
        new_rows.append(new)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=new_cols)
        w.writeheader()
        for r in new_rows:
            w.writerow(r)

    amount_in = sum(float(r["AMT"]) for r in legacy_rows)
    amount_out = sum(float(r["amount_usd"]) for r in new_rows)

    report = (
        f"RECONCILIATION REPORT\n"
        f"=====================\n"
        f"source       : {legacy_csv.name}\n"
        f"target       : {out_csv.name}\n"
        f"rows in      : {len(legacy_rows)}\n"
        f"rows out     : {len(new_rows)}\n"
        f"amount in    : {amount_in:,.2f}\n"
        f"amount out   : {amount_out:,.2f}\n"
        f"row check    : {'OK' if len(legacy_rows) == len(new_rows) else 'MISMATCH'}\n"
        f"amount check : {'OK' if abs(amount_in - amount_out) < 0.005 else 'MISMATCH'}\n"
    )
    out_report.write_text(report, encoding="utf-8")
    log.info("normalize: wrote %s (%d rows)", out_csv, len(new_rows))

    return {
        "rows_in": len(legacy_rows),
        "rows_out": len(new_rows),
        "amount_in_total": amount_in,
        "amount_out_total": amount_out,
        "normalized_file": out_csv,
        "report_file": out_report,
    }
