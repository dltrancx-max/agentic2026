"""Claude-driven computer-use policy (the --live mode).

Replaces MockPolicy.act() with one round trip to Claude per loop step:
  1. screenshot the page  (perceive)
  2. send screenshot + conversation history + tool defs to Claude  (decide)
  3. execute the tool Claude picked  (act)
  4. append the tool result so Claude sees it on the next turn

Critically, this file imports `anthropic` and the SDK is only required for
Live mode — Mock runs never touch it. config.py keeps ANTHROPIC_API_KEY
optional so the rest of the package imports cleanly with no key set.
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

import anthropic
from playwright.sync_api import Page

from agent import tools as t
from agent.computer_use import TimeoutSeen, UnknownPage
from config import (
    ANTHROPIC_API_KEY, DOWNLOAD_DIR, LIVE_MODEL, PASSWORD, USERNAME,
)

log = logging.getLogger("agent.live")


SYSTEM_PROMPT = """\
You are driving a legacy web GUI (LegacyForms 8.3) by looking at screenshots
and choosing one action at a time. Your goal is to extract supply chain
manifests for {quarter} 2025 and click the Export CSV button so they download
as a file.

Credentials (use only on the login screen):
  Username: {username}
  Password: {password}

How to think about it:
  - The browser will keep showing you screenshots after each action.
  - Pick ONE tool call per turn that moves you closer to the goal.
  - When you see results in a table, click Export CSV to finish the task.
  - If you see a "Session Timeout" page or any sign the session expired,
    call report_timeout() — DO NOT try to recover yourself. A long-horizon
    orchestrator owns recovery and will re-invoke you cleanly.
  - If you genuinely cannot make progress, call report_stuck(reason).

You MUST call exactly one tool per turn.
"""


TOOLS = [
    {
        "name": "fill_field",
        "description": "Type text into a form field identified by its visible label (e.g. 'Username', 'Password').",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["label", "value"],
        },
    },
    {
        "name": "select_value",
        "description": "Pick an option in a dropdown identified by its label (e.g. label='Quarter', value='Q3').",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["label", "value"],
        },
    },
    {
        "name": "click_button",
        "description": "Click a button by its visible label. Use for any non-download button: Sign in, Run Query, OK, etc.",
        "input_schema": {
            "type": "object",
            "properties": {"label": {"type": "string"}},
            "required": ["label"],
        },
    },
    {
        "name": "click_button_and_download",
        "description": "Click a button that should trigger a file download (e.g. 'Export CSV'). Use this only when you are ready to save the data and finish the extraction.",
        "input_schema": {
            "type": "object",
            "properties": {"label": {"type": "string"}},
            "required": ["label"],
        },
    },
    {
        "name": "report_timeout",
        "description": "Call this if the current screenshot shows a 'Session Timeout' page or any indication the session expired. The orchestrator will recover.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "report_stuck",
        "description": "Call this if you cannot make progress — unfamiliar page, repeated failures, or the task seems impossible.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


class LivePolicy:
    """Claude-driven decision policy. Stateful across act() calls.

    Each act() call adds one user turn (with a screenshot) and one assistant
    turn (with the chosen tool_use) to self.messages. The tool_result is
    appended after execution so Claude sees outcomes on the next turn.
    """

    name = "LIVE"

    def __init__(self, task: dict):
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "Live mode needs ANTHROPIC_API_KEY. Copy .env.example -> .env "
                "and set your key, or run without --live for Mock mode."
            )
        self.task = task
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.messages: list[dict] = []
        self.system_prompt = SYSTEM_PROMPT.format(
            quarter=task["quarter"], username=USERNAME, password=PASSWORD,
        )

    def act(self, page: Page, perception, audit: list[str]) -> Optional[Path]:
        # 1. PERCEIVE — take a screenshot of the current page.
        png = page.screenshot(type="png", full_page=False)
        b64 = base64.b64encode(png).decode()

        # 2. DECIDE — send screenshot + history to Claude.
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b64},
                },
                {"type": "text", "text": f"URL: {page.url}\nWhat's your next action?"},
            ],
        })

        response = self.client.messages.create(
            model=LIVE_MODEL,
            max_tokens=1024,
            system=self.system_prompt,
            tools=TOOLS,
            messages=self.messages,
        )

        # Persist the assistant response so the next turn has full context.
        self.messages.append({"role": "assistant", "content": response.content})

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_use is None:
            text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
            raise UnknownPage(
                "Claude returned no tool_use. Text: " + " ".join(text_blocks)[:200]
            )

        name = tool_use.name
        args = dict(tool_use.input)
        audit.append(f"  live: tool={name}  args={args}")

        # 3. ACT — execute the chosen tool and capture a tool_result message.
        downloaded: Optional[Path] = None
        tool_result_text = "OK"
        try:
            downloaded, tool_result_text = self._execute_tool(page, name, args, audit)
        except (TimeoutSeen, UnknownPage):
            raise
        except Exception as e:  # any Playwright failure becomes a Claude-visible error
            tool_result_text = f"Error: {type(e).__name__}: {e}"
            log.warning("tool execution failed: %s", tool_result_text)

        # 4. Feed the tool_result back so Claude can react next turn.
        self.messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": tool_result_text,
            }],
        })

        return downloaded

    def _execute_tool(self, page, name, args, audit) -> tuple[Optional[Path], str]:
        """Dispatch one tool call. Returns (downloaded_file_or_None, result_text)."""
        if name == "fill_field":
            t.fill_field(page, args["label"], args["value"], audit)
            return None, "OK"
        if name == "select_value":
            t.select_value(page, args["label"], args["value"], audit)
            return None, "OK"
        if name == "click_button":
            t.click_button(page, args["label"], audit)
            return None, "OK"
        if name == "click_button_and_download":
            dl = t.click_button_and_download(page, args["label"], DOWNLOAD_DIR, audit)
            if dl is not None:
                return dl, f"Downloaded: {dl.name}"
            return None, "No download fired — the click produced a page response instead. Check the next screenshot."
        if name == "report_timeout":
            raise TimeoutSeen()
        if name == "report_stuck":
            raise UnknownPage(args.get("reason", "stuck"))
        raise UnknownPage(f"unknown tool: {name}")
