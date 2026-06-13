# Agentic AI 2026 — Course Materials

Production-developer course on the agentic AI landscape of 2026: the 12 capability blocks, the inflection point where **Long-Horizon Autonomy** × **Computer-Use** unlocks the long tail of legacy systems, and a runnable hands-on practical that turns that scenario into code.

## Read first

- **[2- Enhanced Agentic AI.pdf](2-%20Enhanced%20Agentic%20AI.pdf)** — the main course deck. The 12 capability blocks with deep dives on METR (long-horizon doubling), the Inflection Point (computer-use × long-horizon), and the API-first rule of thumb. Source: [`2- Enhanced Agentic AI.md`](2-%20Enhanced%20Agentic%20AI.md).
- **[design patterns.pdf](design%20patterns.pdf)** — companion reference for the 20 agentic design patterns.
- **[course-plan.md](course-plan.md)** — top-level course structure.

## Hands-on #1 — Legacy Oracle Migration

A small, runnable system that automates a 20-year-old supply-chain workflow with **no API** — a Flask "LegacyForms" GUI behind a Playwright-driven computer-use worker, a checkpointing orchestrator that recovers from an injected session timeout, and a coder step that normalizes the legacy schema to Oracle 23ai.

- **[3 - Hands-on - 1.md](3%20-%20Hands-on%20-%201.md)** — course-level intro (scenario, learning outcomes, run modes, setup walkthrough, troubleshooting, discussion prompts).
- **[hands-on-1/architecture.pdf](hands-on-1/architecture.pdf)** — solution architecture and flow.
- **[hands-on-1/](hands-on-1/)** — the code.

```text
hands-on-1/
  config.py                shared settings
  legacy_app/              Flask GUI with no API, injects one session timeout
  agent/                   computer-use worker (Mock + Claude-live policies)
  orchestrator/            long-horizon state machine + checkpoint + coder
  architecture.{md,pdf,png,py}
```

### Quick start

```powershell
cd hands-on-1
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Run the demo (two terminals):

```powershell
# Terminal 1 — start the legacy GUI
python -m legacy_app.app

# Terminal 2 — run the orchestrator
python -m orchestrator.run                  # Mock (no API key, deterministic)
python -m orchestrator.run --live           # Claude-driven (needs ANTHROPIC_API_KEY)
python -m orchestrator.run --reset          # wipe checkpoint + legacy timeout flag
```

VS Code users can also use the included **Run/Debug** entries (`.vscode/launch.json`) — open this folder and pick "Demo: Flask + Orchestrator (Mock)" to launch both with one click.

See [3 - Hands-on - 1.md](3%20-%20Hands-on%20-%201.md) for the full, beginner-friendly walkthrough.
