# Hands-on #1 — Solution Architecture

### Legacy Oracle Migration: Long-Horizon Autonomy × Computer-Use

This hands-on turns the *Inflection Point* example from the course into a runnable practical. The goal is to **feel** the difference between the two capabilities by watching them cooperate on a job that has **no API** — exactly the kind of "long tail" legacy system that resisted automation for two decades.

![Solution architecture diagram](architecture.png)

---

## How to read it — the flow

**1. The human sets one goal, then walks away.**
An **Enterprise Architect** defines a single high-level objective — *"Extract all Q3 manifests → normalize to Oracle 23ai → migrate; do not stop until the reconciliation report is clean."* — and does **not** script the steps. Everything below is the agentic system figuring out and executing the *how*.

**2. Left zone — Long-Horizon Autonomy (endurance + resilience).**
This is the half that provides *staying power*.

- A plain-Python **Orchestrator** drives a state machine: **EXTRACT → NORMALIZE → DONE**.
- Every step is written to a **Checkpoint** (`checkpoints/state.json`) recording the current phase, attempt count, and file paths — so the job can survive a process kill and **resume exactly where it left off** rather than restarting from zero.
- A `recover()` routine owns the failure path: on a disruption it logs the event, bumps `attempts`, and re-invokes the worker to continue.

**3. Right zone — Computer-Use (unbounded GUI access).**
This is the half that provides *reach* — into software that never exposed an API.

- The **Computer-Use Worker** is Claude (vision) running a **perceive → decide → act** loop: it reads a screenshot, decides the next action, and acts.
- It drives a real **Chromium** browser through Playwright — issuing genuine mouse clicks, keystrokes, and screenshots, the same way a human operator would. No API endpoints are called.
- The target is the **LegacyForms GUI** (a small Flask app): *login → select quarter → run query → export CSV*. It is deliberately **API-free** — HTML forms only — standing in for the legacy Oracle Forms environment behind Citrix.

**4. The disruption — why you need BOTH (red path).**
Mid-export, the legacy system injects a one-time **"Session Timeout."** A rigid RPA script would crash here and wait for a human on Monday. Instead:

- The worker detects the timeout page and reports `status = timeout`.
- That signal **bubbles up** to the orchestrator's `recover()`.
- The orchestrator re-invokes the worker, which **logs back in and finishes the export** — picking up from the checkpoint.

This single beat is the whole point: **computer-use** supplied the unbounded access to the GUI, while **long-horizon autonomy** supplied the endurance and resilience to run unattended and recover from the unexpected.

**5. The output — a clean migration (green path).**
Once **EXTRACT** succeeds, the orchestrator advances to the **NORMALIZE** phase and hands the exported file to a **Coder Agent**, which transforms the legacy data into the new schema (rename columns, convert `DD-MON-YY → ISO` dates) and writes:

- `output/manifests_23ai.csv` — the migrated, normalized data, and
- a **reconciliation report** confirming row counts and totals match.

---

## Legend

| Path | Meaning |
|------|---------|
| **Navy** | Normal control / data flow |
| **Red (dashed)** | Failure & recovery path |
| **Green** | Successful migration output |

## The strategic takeaway

The **computer-use agent** provided the *unbounded access* (manipulating a legacy GUI with no API), while **long-horizon autonomy** provided the *endurance and resilience* (running unattended and recovering from a timeout). Together they let teams automate the messy, unstructured long tail of legacy IT — freeing people for higher-value work.

> **Build order:** legacy GUI app → computer-use worker loop → long-horizon orchestrator (checkpoint + recover) → coder/normalize step. A **mock mode** lets the full demo run without an API key; **live mode** swaps in Claude for the perceive→decide step.
