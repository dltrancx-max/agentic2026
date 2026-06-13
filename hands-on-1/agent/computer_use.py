"""The computer-use worker.

Given a TASK (a small dict like {"goal": "extract", "quarter": "Q3"}) the
worker drives the legacy GUI through a perceive -> decide -> act loop until it
either completes the task or hits a wall it doesn't know how to handle.

Critically, the worker does NOT know about the long-horizon orchestrator or
checkpoints. It returns a small status object and lets the orchestrator decide
what to do next. That separation is what makes the system survive a timeout:
the worker reports failure, the orchestrator owns recovery.

Two policies share the same loop:
  * MockPolicy  -- deterministic, no API key, no cost.
  * LivePolicy  -- Claude vision + tool-use (added in a later step).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from playwright.sync_api import Page, sync_playwright

from agent import tools
from config import (
    BASE_URL, DOWNLOAD_DIR, MAX_WORKER_STEPS,
    PASSWORD, TARGET_QUARTER, USERNAME,
)

log = logging.getLogger("agent.worker")

Status = Literal["success", "timeout", "error"]


@dataclass
class WorkerResult:
    status: Status
    downloaded_file: Optional[Path] = None
    error: Optional[str] = None
    audit: list[str] = field(default_factory=list)


# --- the perceive step: what page are we on? --------------------------------

@dataclass
class Perception:
    """A tiny structured view of the current page state."""
    label: str  # human-readable name for the audit log

    @property
    def kind(self) -> str:
        return self.label


def perceive(page: Page) -> Perception:
    """Read the page and classify what kind of screen it is."""
    if tools.is_timeout_page(page):
        return Perception("TIMEOUT_PAGE")
    if tools.is_login_page(page):
        return Perception("LOGIN_PAGE")
    if tools.has_results_with_export(page):
        return Perception("RESULTS_WITH_EXPORT")
    if tools.is_manifests_page_idle(page):
        return Perception("MANIFESTS_IDLE")
    return Perception("UNKNOWN")


# --- the deterministic Mock policy ------------------------------------------
#
# This is the demo's "decide" step. Each branch maps a perceived page kind to
# the action(s) we should take. In LiveMode this whole function is replaced by
# Claude looking at a screenshot and choosing actions itself; the shape of the
# loop stays identical, which is the point.

class MockPolicy:
    """Deterministic policy hard-coded to the LegacyForms flow."""

    name = "MOCK"

    def __init__(self, task: dict):
        self.task = task

    def act(self, page: Page, perception: Perception, audit: list[str]) -> Optional[Path]:
        """Execute the action(s) for the current perception.

        Returns a Path if a file was downloaded this step, else None.
        Raises TimeoutSeen on the timeout page so the loop can exit cleanly.
        """
        kind = perception.kind
        if kind == "LOGIN_PAGE":
            tools.fill_field(page, "Username", USERNAME, audit)
            tools.fill_field(page, "Password", PASSWORD, audit)
            tools.click_button(page, "Sign in", audit)
            return None

        if kind == "MANIFESTS_IDLE":
            tools.select_value(page, "Quarter", self.task["quarter"], audit)
            tools.click_button(page, "Run Query", audit)
            return None

        if kind == "RESULTS_WITH_EXPORT":
            return tools.click_button_and_download(
                page, "Export CSV", DOWNLOAD_DIR, audit
            )

        if kind == "TIMEOUT_PAGE":
            raise TimeoutSeen()

        raise UnknownPage(f"no rule for perception={kind!r} url={page.url}")


# --- internal control-flow sentinels ----------------------------------------

class TimeoutSeen(Exception):
    """Raised by a policy when it sees the Session Timeout page."""


class UnknownPage(Exception):
    """Raised when no rule matches the current page."""


# --- the worker loop --------------------------------------------------------

def run_worker(
    task: dict,
    *,
    mode: str = "mock",
    headless: bool = False,
    slow_mo_ms: int = 350,
) -> WorkerResult:
    """One invocation of the computer-use worker.

    The orchestrator calls this. On timeout the worker returns
    status='timeout' rather than retrying internally -- recovery is the
    orchestrator's job.
    """
    audit: list[str] = []
    policy = _build_policy(mode, task)
    audit.append(f"worker start  task={task}  policy={policy.name}  mode={mode}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()
        try:
            tools.goto(page, BASE_URL, audit)

            for step in range(1, MAX_WORKER_STEPS + 1):
                perception = perceive(page)
                audit.append(
                    f"step {step:>2}: perceive {page.url!s:40} -> {perception.kind}"
                )
                try:
                    downloaded = policy.act(page, perception, audit)
                except TimeoutSeen:
                    audit.append("  !!  TIMEOUT_PAGE seen — bailing out")
                    return WorkerResult(status="timeout", audit=audit)
                except UnknownPage as e:
                    audit.append(f"  !!  {e}")
                    return WorkerResult(status="error", error=str(e), audit=audit)

                if downloaded is not None:
                    audit.append(f"worker done   downloaded={downloaded}")
                    return WorkerResult(
                        status="success", downloaded_file=downloaded, audit=audit,
                    )

                # Wait briefly for the next page to settle before re-perceiving.
                page.wait_for_load_state("domcontentloaded")

            return WorkerResult(
                status="error",
                error=f"exceeded MAX_WORKER_STEPS={MAX_WORKER_STEPS}",
                audit=audit,
            )
        finally:
            ctx.close()
            browser.close()


def _build_policy(mode: str, task: dict):
    if mode == "mock":
        return MockPolicy(task)
    if mode == "live":
        from agent.live_policy import LivePolicy  # imported lazily; live is optional
        return LivePolicy(task)
    raise ValueError(f"unknown worker mode: {mode!r}")


# --- standalone smoke entry point -------------------------------------------

def main() -> None:
    """`python -m agent.computer_use` — drive the legacy app once, mock mode."""
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    res = run_worker({"goal": "extract", "quarter": TARGET_QUARTER}, mode="mock")
    print("\n--- audit ---")
    for line in res.audit:
        print(line)
    print(f"\n--- result: status={res.status}  file={res.downloaded_file}  err={res.error}")


if __name__ == "__main__":
    main()
