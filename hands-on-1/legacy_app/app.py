"""LegacyForms — a Flask stand-in for the legacy Oracle Forms GUI.

Deliberately retro: HTML forms only, no JSON endpoints, no API. Everything the
worker does it does by clicking and typing — the same way a human operator
would. This is the "system that never got an API" in the practical.

Run standalone:
    python -m legacy_app.app
"""
from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

from flask import (
    Flask, redirect, render_template, request,
    session, send_file, url_for,
)

from config import (
    BASE_URL, DATA_FILE, FLASK_SECRET, LEGACY_HOST, LEGACY_PORT,
    PASSWORD, SUPPORTED_QUARTERS, TIMEOUT_AFTER, USERNAME,
)

log = logging.getLogger("legacy_app")

app = Flask(__name__)
app.secret_key = FLASK_SECRET

# Endpoints that require an authenticated session. The session-timeout
# disruption only counts requests against these — public pages don't count.
_PROTECTED = {"manifests", "run_query", "export_csv", "logout"}

# Module-level state: a single counter and a "did the disruption already fire?"
# flag. Demo only — fine because this is a single-user toy. A real app would
# use a server-side session store or a per-user db row.
_state: dict = {"protected_calls": 0, "timeout_already_fired": False}


# --- helpers -----------------------------------------------------------------

def _logged_in() -> bool:
    return session.get("user") == USERNAME


def _load_manifests() -> list[dict]:
    with DATA_FILE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _quarter_of(ship_dt: str) -> str:
    """Map DD-MON-YY -> Q1..Q4 based on the month token."""
    month = ship_dt.split("-")[1].upper()
    return {
        "JAN": "Q1", "FEB": "Q1", "MAR": "Q1",
        "APR": "Q2", "MAY": "Q2", "JUN": "Q2",
        "JUL": "Q3", "AUG": "Q3", "SEP": "Q3",
        "OCT": "Q4", "NOV": "Q4", "DEC": "Q4",
    }.get(month, "??")


# --- the session-timeout disruption ------------------------------------------

@app.before_request
def maybe_inject_timeout():
    """Fire the one-shot 'Session Timeout' on a session-protected request.

    This is the disruption the long-horizon orchestrator has to recover from.
    Counts ONLY against protected endpoints (so static assets and login itself
    don't burn the counter), fires once per server lifetime, and clears the
    session so the agent must log back in to continue.
    """
    ep = request.endpoint
    if ep not in _PROTECTED:
        return None
    _state["protected_calls"] += 1
    if (
        TIMEOUT_AFTER
        and _state["protected_calls"] >= TIMEOUT_AFTER
        and not _state["timeout_already_fired"]
    ):
        _state["timeout_already_fired"] = True
        log.warning(
            "Injecting Session Timeout (protected_calls=%d, endpoint=%s)",
            _state["protected_calls"], ep,
        )
        session.clear()
        return render_template("timeout.html"), 440  # 440: Login Time-out
    return None


# --- routes ------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("manifests" if _logged_in() else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = (request.form.get("password") or "").strip()
        if u == USERNAME and p == PASSWORD:
            session["user"] = u
            return redirect(url_for("manifests"))
        error = "Invalid credentials. Try again."
    return render_template("login.html", error=error)


@app.route("/manifests")
def manifests():
    if not _logged_in():
        return redirect(url_for("login"))
    return render_template(
        "manifests.html",
        quarters=SUPPORTED_QUARTERS,
        results=None,
        selected_quarter=None,
    )


@app.route("/query", methods=["POST"])
def run_query():
    if not _logged_in():
        return redirect(url_for("login"))
    q = (request.form.get("quarter") or "").strip().upper()
    if q not in SUPPORTED_QUARTERS:
        return render_template(
            "manifests.html",
            quarters=SUPPORTED_QUARTERS,
            results=None,
            selected_quarter=None,
            error=f"Unknown quarter: {q!r}",
        )
    rows = [r for r in _load_manifests() if _quarter_of(r["SHIP_DT"]) == q]
    return render_template(
        "manifests.html",
        quarters=SUPPORTED_QUARTERS,
        results=rows,
        selected_quarter=q,
    )


@app.route("/export", methods=["POST"])
def export_csv():
    if not _logged_in():
        return redirect(url_for("login"))
    q = (request.form.get("quarter") or "").strip().upper()
    if q not in SUPPORTED_QUARTERS:
        return redirect(url_for("manifests"))
    rows = [r for r in _load_manifests() if _quarter_of(r["SHIP_DT"]) == q]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    writer.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    return send_file(
        io.BytesIO(data),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"manifests_{q.lower()}_2025.csv",
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- admin: reset the disruption so the demo can be re-run -------------------

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    _state["protected_calls"] = 0
    _state["timeout_already_fired"] = False
    session.clear()
    return ("reset ok", 200, {"Content-Type": "text/plain"})


# --- main --------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    log.info("LegacyForms starting on %s (timeout after %s protected calls)",
             BASE_URL, TIMEOUT_AFTER or "never")
    app.run(host=LEGACY_HOST, port=LEGACY_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
