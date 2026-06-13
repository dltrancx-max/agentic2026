"""Thin Playwright wrappers — the only way the worker touches the browser.

Why isolate them here:
  * one place to add audit logging (every action records a line)
  * one place to swap selector strategy if we ever ditch role-based queries
  * makes computer_use.py read like a state machine, not Playwright glue
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


# --- perception (read-only) --------------------------------------------------

def page_text(page: Page) -> str:
    """The visible body text. What the agent 'sees' beyond the screenshot."""
    return page.inner_text("body")


def is_timeout_page(page: Page) -> bool:
    return "Session Timeout" in page_text(page)


def is_login_page(page: Page) -> bool:
    text = page_text(page)
    # H2 "Sign in" + the two field labels. NOTE: submit-button labels live in
    # the <input value="..."> attribute, NOT in inner_text — so we can't rely
    # on the button's visible label being present in body text.
    return "Sign in" in text and "Username" in text and "Password" in text


def has_results_with_export(page: Page) -> bool:
    text = page_text(page)
    # Results table renders MANIFEST_NO as a column header, which is in text.
    # When results are non-empty the Export CSV button is also rendered.
    return "Results" in text and "MANIFEST_NO" in text


def is_manifests_page_idle(page: Page) -> bool:
    """Manifests page is loaded but no query has been run yet."""
    text = page_text(page)
    return (
        "Supply Chain Manifests" in text
        and "Quarter" in text          # the dropdown label
        and "Results" not in text       # no query has been run yet
    )


# --- actions (mutate the page) ----------------------------------------------

def fill_field(page: Page, label: str, value: str, audit: list[str]) -> None:
    page.get_by_label(label).fill(value)
    audit.append(f"  act:  fill   {label!r:18} = {value!r}")


def select_value(page: Page, label: str, value: str, audit: list[str]) -> None:
    page.get_by_label(label).select_option(value)
    audit.append(f"  act:  select {label!r:18} = {value!r}")


def click_button(page: Page, label: str, audit: list[str]) -> None:
    page.get_by_role("button", name=label).click()
    audit.append(f"  act:  click  button {label!r}")


def click_button_and_download(
    page: Page,
    label: str,
    save_dir: Path,
    audit: list[str],
    timeout_ms: int = 4000,
) -> Optional[Path]:
    """Click a button that *should* trigger a file download.

    Returns the saved Path on success. Returns None if the click instead
    triggered a page response (e.g. the Session Timeout page) — the worker
    loop will pick that up on the next perceive cycle.
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    try:
        with page.expect_download(timeout=timeout_ms) as info:
            page.get_by_role("button", name=label).click()
    except PlaywrightTimeoutError:
        audit.append(f"  act:  click  button {label!r}  (no download — page response)")
        return None
    dl = info.value
    target = save_dir / dl.suggested_filename
    dl.save_as(target)
    audit.append(f"  act:  click  button {label!r}  ->  download {target.name}")
    return target


def goto(page: Page, url: str, audit: list[str]) -> None:
    page.goto(url, wait_until="domcontentloaded")
    audit.append(f"  act:  goto   {url}")
