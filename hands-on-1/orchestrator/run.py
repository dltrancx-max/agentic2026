"""The long-horizon orchestrator.

It owns three things the worker does NOT:
  1. The goal      — what we're trying to achieve overall.
  2. The state     — a small JSON checkpoint written after every transition,
                     so the run can resume after a crash, kill, or reboot.
  3. The recovery  — on a worker timeout it logs, bumps `attempts`, and
                     re-invokes the worker. The worker has no idea.

State machine:
    EXTRACT  → invoke the computer-use worker
              ├── success  → advance to NORMALIZE
              ├── timeout  → recover (bump attempts), stay in EXTRACT
              └── error    → bail
    NORMALIZE → run the Coder step on the downloaded CSV
              └── success  → advance to DONE
    DONE     → print reconciliation report, exit

Run from the repo root:
    python -m orchestrator.run                 # mock policy (no API key)
    python -m orchestrator.run --live          # Claude-driven worker
    python -m orchestrator.run --reset         # wipe checkpoint + legacy state
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from agent.computer_use import run_worker
from config import (
    BASE_URL, CHECKPOINT_FILE, DOWNLOAD_DIR, MAX_EXTRACT_RETRIES,
    NORMALIZED_FILE, OUTPUT_DIR, RECONCILIATION_FILE,
    TARGET_QUARTER, ensure_dirs,
)
from orchestrator.coder_step import normalize

log = logging.getLogger("orchestrator")


# --- the checkpointable state -----------------------------------------------

@dataclass
class State:
    phase: str = "EXTRACT"
    attempts: int = 0
    extracted_file: Optional[str] = None
    normalized_file: Optional[str] = None
    quarter: str = TARGET_QUARTER
    started_at: float = field(default_factory=time.time)
    last_event: str = "init"

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


# --- recovery ---------------------------------------------------------------

def recover(state: State, reason: str) -> None:
    """Handle a worker failure that's worth retrying.

    All we do here is record what happened. The next loop iteration
    re-invokes the worker, which will re-perceive the page state (it will
    see the LOGIN_PAGE because the legacy app cleared the session) and
    work its way back through the flow.
    """
    state.attempts += 1
    state.last_event = f"recover({reason}) attempt={state.attempts}"
    log.warning(state.last_event)


# --- the main loop ----------------------------------------------------------

def run(mode: str = "mock", headless: bool = False) -> int:
    ensure_dirs()
    state = State.load(CHECKPOINT_FILE)
    log.info("loaded state: %s", asdict(state))

    while state.phase != "DONE":
        if state.phase == "EXTRACT":
            if state.attempts >= MAX_EXTRACT_RETRIES:
                log.error("EXTRACT exceeded MAX_EXTRACT_RETRIES=%d — bailing",
                          MAX_EXTRACT_RETRIES)
                return 2

            log.info("EXTRACT  attempt=%d  delegating to worker (%s)…",
                     state.attempts + 1, mode)
            result = run_worker(
                {"goal": "extract", "quarter": state.quarter},
                mode=mode, headless=headless,
            )
            for line in result.audit:
                log.info("worker | %s", line)

            if result.status == "success":
                assert result.downloaded_file is not None
                state.extracted_file = str(result.downloaded_file)
                state.phase = "NORMALIZE"
                state.last_event = f"extract ok: {result.downloaded_file.name}"
                state.save(CHECKPOINT_FILE)
                log.info("EXTRACT  -> %s  advancing to NORMALIZE",
                         result.downloaded_file.name)
            elif result.status == "timeout":
                recover(state, "session-timeout")
                state.save(CHECKPOINT_FILE)
                # loop continues — re-invoke the worker.
            else:
                log.error("EXTRACT  worker error: %s", result.error)
                state.last_event = f"extract error: {result.error}"
                state.save(CHECKPOINT_FILE)
                return 3

        elif state.phase == "NORMALIZE":
            assert state.extracted_file is not None
            stats = normalize(Path(state.extracted_file))
            state.normalized_file = str(stats["normalized_file"])
            state.phase = "DONE"
            state.last_event = (
                f"normalize ok: {stats['rows_out']} rows  "
                f"amount={stats['amount_out_total']:.2f}"
            )
            state.save(CHECKPOINT_FILE)
            log.info("NORMALIZE -> %s  advancing to DONE",
                     stats["normalized_file"].name)
        else:
            log.error("unknown phase %r", state.phase)
            return 4

    # DONE — print the report and finish.
    print()
    print(RECONCILIATION_FILE.read_text(encoding="utf-8"))
    print(f"Normalized CSV : {state.normalized_file}")
    print(f"Recovery count : {state.attempts}  (each was a Session Timeout the worker recovered from)")
    return 0


# --- reset utility ----------------------------------------------------------

def reset() -> int:
    """Wipe local state and reset the legacy app's timeout flag.

    Useful between class demos so the disruption fires again next run.
    """
    removed: list[str] = []
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        removed.append(str(CHECKPOINT_FILE))
    if DOWNLOAD_DIR.exists():
        shutil.rmtree(DOWNLOAD_DIR)
        removed.append(str(DOWNLOAD_DIR))
    if NORMALIZED_FILE.exists():
        NORMALIZED_FILE.unlink()
        removed.append(str(NORMALIZED_FILE))
    if RECONCILIATION_FILE.exists():
        RECONCILIATION_FILE.unlink()
        removed.append(str(RECONCILIATION_FILE))

    legacy_reset_ok = False
    try:
        req = urllib.request.Request(f"{BASE_URL}/admin/reset", method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=2.0) as r:
            legacy_reset_ok = r.status == 200
    except (urllib.error.URLError, ConnectionError) as e:
        log.warning("could not reach legacy app at %s: %s "
                    "(start it first if you want the timeout flag reset)",
                    BASE_URL, e)

    print(f"removed: {len(removed)} item(s)")
    for r in removed:
        print(f"  - {r}")
    print(f"legacy app reset: {'OK' if legacy_reset_ok else 'skipped (app not running)'}")
    return 0


# --- CLI --------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--live", action="store_true",
                        help="use Claude-driven LivePolicy (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--reset", action="store_true",
                        help="wipe checkpoint + outputs + legacy timeout flag, then exit")
    parser.add_argument("--headless", action="store_true",
                        help="run the browser headless (default is visible so you can watch)")
    args = parser.parse_args()

    if args.reset:
        sys.exit(reset())

    rc = run(mode="live" if args.live else "mock", headless=args.headless)
    sys.exit(rc)


if __name__ == "__main__":
    main()
