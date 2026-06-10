# Hands-on #1 — Legacy Oracle Migration

### Long-Horizon Autonomy × Computer-Use, on a system that has *no API*

This practical turns the *Inflection Point* example from the course into a small, runnable system you can drive yourself. The goal is not to write a clever agent — it is to **feel**, in your own terminal, why the combination of **Long-Horizon Autonomy** and **Computer-Use** is the inflection point that lets agents finally automate the messy long tail of legacy IT.

> If you have not read it yet, skim the *"The Inflection Point: Long-Horizon Autonomy & Computer-Use"* section of [2- Enhanced Agentic AI.pdf](2-%20Enhanced%20Agentic%20AI.pdf) first — this hands-on is the literal scenario described there.

---

## The scenario you are automating

You are migrating **20 years of supply-chain manifests** from a legacy **Oracle 8i** environment up to a modern **Oracle 23ai** infrastructure.

The legacy system has the properties that make this hard:

- It sits behind a Citrix-style terminal and exposes an old **Oracle Forms GUI** — no REST API, no webhooks, no export endpoint.
- The only way to get data out is the same way a human analyst would: **log in, choose a quarter, run the query, click Export.**
- It is unreliable — sessions time out without warning, and a single "Session Timeout" pop-up will crash any rigid RPA script written against it.

The mandate from the architect is **one sentence**:

> *"Extract all Q3 supply chain manifests, normalize the schema to match the new Oracle 23ai standard, and execute the migration. Do not stop until the reconciliation report is clean."*

That is the only instruction the system is given. Everything else — the click order, the recovery, the schema rewrite — it figures out.

---

## What you will learn (the *feel*, not the code)

After running this end to end, you should be able to answer these without notes:

1. **Why "computer-use" is *not* just RPA with extra steps.** You will watch the agent re-read the screen after every action and adapt — vs. an RPA script that breaks the moment a button moves.
2. **What "long-horizon autonomy" actually buys you.** You will trigger a mid-run failure (a forced session timeout). A rigid pipeline would die on Monday morning. The orchestrator will checkpoint, recover, log back in, and finish — *unattended*.
3. **Why you need *both*.** Computer-use alone gets you reach but no resilience. Long-horizon alone gets you persistence but no way into systems without APIs. The two together are what makes the legacy long tail addressable.
4. **The production-developer concerns** that come straight at you the moment this stops being a toy: scoped credentials, sandboxed browsers, action audit logs, human-in-the-loop gates on irreversible steps, and the *"API first, MCP server second, GUI agent last"* rule of thumb.

---

## Solution architecture

The full diagram and a step-by-step walkthrough live at [hands-on-1/architecture.pdf](hands-on-1/architecture.pdf). The short version:

![Hands-on #1 architecture](hands-on-1/architecture.png)

Two cooperating capabilities, each owning one half of the problem:

**1 · Long-Horizon Autonomy (left, navy zone)** — the *endurance*.
- A plain-Python **Orchestrator** drives a state machine: **EXTRACT → NORMALIZE → DONE**.
- Every step is written to a **Checkpoint** (`checkpoints/state.json`) so the run survives a process kill and resumes where it left off.
- `recover()` owns the failure path: on a disruption it logs, bumps `attempts`, and re-invokes the worker.

**2 · Computer-Use (right, cyan zone)** — the *reach*.
- A **Worker** runs a **perceive → decide → act** loop: read screenshot, pick action, execute.
- It drives a real **Chromium** browser via Playwright — genuine clicks and keystrokes, no API calls.
- The target is a small **LegacyForms** Flask app standing in for the legacy Oracle Forms GUI. It is intentionally API-free.

**The disruption (red path).** Mid-export, the legacy system injects a one-time *"Session Timeout."* The worker reports `status = timeout`; the orchestrator's `recover()` catches it and re-invokes the worker, which logs back in and finishes the job.

**The output (green path).** Once EXTRACT succeeds, the **NORMALIZE** phase runs a small Coder Agent that converts the legacy CSV (rename columns, `DD-MON-YY → ISO` dates) into `output/manifests_23ai.csv` plus a **reconciliation report**.

---

## What you will build

Four parts, in build order:

| # | Component | Role | Lives in |
|---|-----------|------|----------|
| 1 | **LegacyForms GUI** (Flask) | The thing being driven. HTML forms only, no API. Has an injectable session timeout. | `hands-on-1/legacy_app/` |
| 2 | **Computer-Use Worker** | Playwright + Claude (vision). Perceive→decide→act loop. Returns `status = success / timeout`. | `hands-on-1/agent/` |
| 3 | **Long-Horizon Orchestrator** | Python state machine + JSON checkpoint + `recover()`. Owns the *goal*, not the clicks. | `hands-on-1/orchestrator/` |
| 4 | **Coder step (NORMALIZE)** | Reads the exported legacy CSV; writes 23ai-schema CSV + reconciliation report. | `hands-on-1/orchestrator/coder_step.py` |

The split is intentional and worth absorbing: **the worker has no idea what the goal is**, and **the orchestrator has no idea how to click a button**. They communicate through a tiny status contract. That separation is what makes the system survive a timeout — the worker returns *failure*, the orchestrator owns *what to do about it*.

---

## Two ways to run it

The build supports two modes. They are **identical from the user's perspective** — same legacy app, same orchestrator, same checkpoint logic — only the *decide* step changes.

| Mode | What replaces the *decide* step | Needs an API key? | Cost | When to use it |
|------|---------------------------------|-------------------|------|----------------|
| **Mock** | A deterministic Python policy that knows the LegacyForms app's flow. | No | Zero | Class machines without keys; running the demo offline; lecture replay. |
| **Live** | **Claude** with vision (the screenshot) + tool-use (click / type / select / finish). | Yes (`ANTHROPIC_API_KEY`) | A few cents per full run | Showing real model-driven control; demonstrating how the agent recovers from an unexpected timeout *without* having seen one before. |

Both modes hit the same legacy app, take the same screenshots, trigger the same forced timeout, and emit the same reconciliation report. Mock proves the *architecture* works; Live proves the *agent* does.

---

## Setup (step by step, for a first-time user)

You can do this entirely on your own machine. Total time: ~10 minutes (most of it is two downloads). Total disk: ~500 MB (Python packages + Chromium browser).

### 0. Prerequisites — what you need installed first

You only need two things on your computer before starting:

- **Python 3.10 or newer.** Check what you have:
  ```powershell
  python --version
  ```
  If the command isn't found or shows 3.9 or older, install the latest from [python.org/downloads](https://python.org/downloads). On Windows, **tick "Add Python to PATH"** during install — otherwise `python` won't work in your terminal.
- **git.** Check with `git --version`. If missing, install from [git-scm.com](https://git-scm.com).

That's it. You do **not** need to install Chromium, Node.js, Docker, or any Anthropic SDK separately — the next steps handle all of that.

### 1. Get the code

If you haven't already, clone the repo (or download it as a ZIP from GitHub):

```powershell
git clone https://github.com/dltrancx-max/agentic2026.git
cd agentic2026
```

If you already cloned it, just `cd` into the folder.

### 2. Move into the hands-on folder

Everything below runs from inside `hands-on-1/`:

```powershell
cd hands-on-1
```

### 3. Create a virtual environment (`venv`)

A **virtual environment** is an isolated Python install that lives in a folder *next to your project* (here: `.venv/`). It exists so the packages this practical needs don't pollute your global Python or fight with other projects. If you ever want to start over, just delete the `.venv/` folder.

```powershell
python -m venv .venv
```

This creates `.venv/` in about 5 seconds. No download — it just copies your existing Python into that folder.

### 4. Activate the venv

Activation tells your terminal *"when I say `python` or `pip`, use the one inside `.venv/`."* You'll know it worked when your prompt gets a `(.venv)` prefix.

The exact command depends on your shell:

```powershell
# PowerShell (default on Windows 10/11)
.venv\Scripts\Activate.ps1
```
```
:: Command Prompt (cmd.exe)
.venv\Scripts\activate.bat
```
```bash
# Git Bash on Windows
source .venv/Scripts/activate
# macOS / Linux
source .venv/bin/activate
```

**PowerShell troubleshooting.** If you see `running scripts is disabled on this system`, run this *once* (per machine) in an Administrator PowerShell, then try again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Sanity check that activation worked:
```powershell
python -c "import sys; print(sys.executable)"
# should print a path ending in ...hands-on-1\.venv\Scripts\python.exe
```

### 5. Install the Python dependencies

`requirements.txt` lists everything the practical needs (Flask, Playwright, the Anthropic SDK, python-dotenv, matplotlib). Install them into the venv:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Downloads ~150 MB of packages and takes 1–3 minutes depending on your connection. When it finishes you'll see a single line like:

```
Successfully installed annotated-types-0.7.0 anthropic-0.109.1 ... flask-3.1.3 ... playwright-1.60.0 ...
```

> **Tip:** Using `python -m pip` instead of plain `pip` guarantees you're installing into the **same** Python that's currently active. It's the safest habit on Windows where multiple Pythons often coexist.

### 6. Install the Chromium browser for Playwright

Playwright is the library that drives a real browser. The `pip install` in step 5 installed the **library**, but not the **browser itself** — that's a separate ~150 MB download:

```powershell
python -m playwright install chromium
```

This downloads two things into your user profile (not into the project):

- **Chrome for Testing** (~180 MB) — the browser Playwright opens visibly so you can watch the agent click.
- **Chrome Headless Shell** (~110 MB) — a smaller, no-window version used for headless runs.

When it's done you'll see two `downloaded to ...\AppData\Local\ms-playwright\...` lines. Total disk after this step: ~200 MB inside `.venv/` + ~300 MB in `ms-playwright/`.

### 7. (Live mode only) Create your `.env` file

The practical has two modes:

- **Mock mode** (default) — uses a deterministic Python policy for the *decide* step. **No API key, no cost.** This is what you should run first.
- **Live mode** — Claude decides each action from a screenshot. Needs an Anthropic API key.

If you only want to run Mock mode, **skip this step.** For Live mode, create your env file:

```powershell
# PowerShell or cmd
copy .env.example .env

# Git Bash / macOS / Linux
cp .env.example .env
```

Open `.env` in your editor and set the key:

```dotenv
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

Get a key from [console.anthropic.com](https://console.anthropic.com) → **Settings → API Keys → Create Key**. Treat it like a password — `.env` is already listed in `.gitignore`, so it won't be accidentally committed.

### 8. Verify the setup (smoke test)

Paste this one-liner into your terminal to confirm imports work and Playwright can actually launch a browser:

```powershell
python -c "import flask, anthropic; from playwright.sync_api import sync_playwright; import importlib.metadata as m; print('flask    ', m.version('flask')); print('anthropic', anthropic.__version__); print('playwright', m.version('playwright')); print('dotenv   ', m.version('python-dotenv')); p = sync_playwright().start(); b = p.chromium.launch(headless=True); page = b.new_page(); page.set_content('<h1>hello legacy</h1>'); print('rendered :', page.inner_text('h1')); b.close(); p.stop(); print('OK - smoke test passed')"
```

Expected output:

```
flask     3.1.3
anthropic 0.109.1
playwright 1.60.0
dotenv    1.2.2
rendered : hello legacy
OK - smoke test passed
```

If you see those six lines, **everything is wired up** and you're ready to run the practical. If you hit an error, see the *Troubleshooting* table below.

### Troubleshooting cheat-sheet

| Symptom | What it means | Fix |
|---|---|---|
| `python : The term 'python' is not recognized` | Python isn't on your PATH. | Reinstall Python with **Add to PATH** checked, then open a new terminal. |
| `running scripts is disabled on this system` when activating | PowerShell's default policy blocks scripts. | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once. |
| `(.venv)` prefix never appears in the prompt | Activation didn't take effect. | Use the activate command for *your* shell (PowerShell vs cmd vs bash) and check `python -c "import sys; print(sys.executable)"` points inside `.venv/`. |
| `ModuleNotFoundError: No module named 'flask'` | Wrong Python is being used. | Re-activate the venv, then re-check `sys.executable`. |
| `Executable doesn't exist at ...\ms-playwright\chromium-...` | Step 6 was skipped. | Run `python -m playwright install chromium`. |
| `anthropic.AuthenticationError` (Live mode only) | API key missing or wrong. | Confirm `.env` has `ANTHROPIC_API_KEY=sk-ant-...` with no quotes or spaces; re-run. |
| `DeprecationWarning: '__version__' attribute is deprecated` | Harmless future-Flask warning. | Ignore. |

---

## Running the demo

Once the build is complete you will have one entrypoint:

```bash
# Terminal 1 — start the legacy GUI
python -m legacy_app.app

# Terminal 2 — run the orchestrator (mock mode by default)
python -m orchestrator.run                  # mock
python -m orchestrator.run --live           # Claude-driven
python -m orchestrator.run --reset          # wipe checkpoint + legacy timeout flag
```

What you should see, in this order:
1. Chromium opens, you watch the worker log in, pick **Q3**, run the query, and click **Export**.
2. The forced timeout fires; the worker reports `status = timeout` and exits.
3. The orchestrator logs the failure, writes the checkpoint, and re-invokes the worker.
4. The worker logs back in and completes the export.
5. The Coder step normalizes the CSV and prints the reconciliation report.
6. `output/manifests_23ai.csv` and `output/reconciliation.txt` appear.

If you kill the orchestrator with `Ctrl+C` at any point and re-run it, it picks up from the last checkpoint — that is the long-horizon resilience guarantee in action.

---

## What to discuss in class (after running it)

- **Where would you put a human-in-the-loop gate**, and why? (Hint: the *write* side of NORMALIZE, not the read side of EXTRACT.)
- **What is the smallest credential scope** this agent could have? Could the legacy account be read-only? Could the export be staged through a separate identity?
- **How would you audit this run** if someone asked *"prove you didn't change a single row"* a quarter later? What gets logged, where, for how long?
- **Where does this approach break?** What if the legacy system asks for a 2FA code? Captures a CAPTCHA? Locks the account after N failed logins? Map each failure mode to a control.
- **API first, MCP second, GUI agent last** — what would it take to retire the GUI agent here? Is there a path to a thin export API on the legacy side? At what point is *that* cheaper than keeping the agent?

---

## The strategic takeaway

The **computer-use** agent provided the **unbounded access** (manipulating a legacy GUI with no API). **Long-horizon autonomy** provided the **endurance and resilience** (running unattended and recovering from a timeout). Together, they let teams automate the messy, unstructured *long tail* of legacy IT operations — freeing human capital for strategic work, not manual data investigation.

> **Build order:** legacy GUI app → computer-use worker → long-horizon orchestrator (checkpoint + recover) → coder/normalize step. The mock policy lets the whole demo run without an API key; flip to `--live` to swap in Claude for the *decide* step.
