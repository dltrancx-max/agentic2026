"""Render the Hands-on #1 solution architecture diagram to architecture.png.

Pure matplotlib (no graphviz needed). Re-run after edits:
    python architecture.py

Note: DejaVu Sans (matplotlib's default) has no colour-emoji glyphs, so any
emoji in label text would render as tofu boxes. _clean() strips them at render
time, making this robust even if emoji sneak back into the literals.
"""
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

# ---- palette (matches the course PDF theme) ---------------------------------
NAVY = "#0a2342"
BLUE = "#1565c0"
CYAN = "#00bcd4"
LCYAN = "#e8f6fb"
LBLUE = "#eef4fb"
GREY = "#90a4ae"
RED = "#c62828"
LRED = "#fdecea"
GREEN = "#2e7d32"
LGREEN = "#e8f5e9"
INK = "#1a1a1a"

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U0000200D\U000020E3]")


def _clean(text):
    """Drop emoji/symbol glyphs DejaVu Sans can't render, tidy stray spaces."""
    return re.sub(r"^\s+", "", _EMOJI.sub("", text))


fig, ax = plt.subplots(figsize=(14.5, 10), dpi=150)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, text, fc="white", ec=NAVY, tc=INK, fs=10, bold=False,
        style="round", lw=1.6, ls="-"):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"{style},pad=0.02,rounding_size=0.8",
                       fc=fc, ec=ec, lw=lw, ls=ls, zorder=2)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, _clean(text), ha="center", va="center",
            fontsize=fs, color=tc, zorder=3,
            fontweight="bold" if bold else "normal", wrap=True)


def zone(x, y, w, h, label, fc, ec):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.02,rounding_size=1.4",
                       fc=fc, ec=ec, lw=2, ls=(0, (6, 4)), zorder=1, alpha=0.55)
    ax.add_patch(p)
    ax.text(x + 1.5, y + h - 1.6, _clean(label), ha="left", va="top",
            fontsize=11.5, color=ec, fontweight="bold", zorder=3)


def arrow(x1, y1, x2, y2, color=NAVY, ls="-", lw=1.8, label=None,
          lx=None, ly=None, lcolor=None, rad=0.0, fs=8.5):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        connectionstyle=f"arc3,rad={rad}",
                        arrowstyle="-|>", mutation_scale=16,
                        color=color, lw=lw, ls=ls, zorder=4)
    ax.add_patch(a)
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2,
                ly if ly is not None else (y1 + y2) / 2,
                _clean(label), ha="center", va="center", fontsize=fs,
                color=lcolor or color, zorder=5,
                bbox=dict(boxstyle="round,pad=0.18", fc="white",
                          ec="none", alpha=0.9))


# ---- title ------------------------------------------------------------------
ax.text(50, 97.5, "Hands-on #1 - Legacy Oracle Migration",
        ha="center", va="center", fontsize=18, color=NAVY, fontweight="bold")
ax.text(50, 94.2,
        "Long-Horizon Autonomy  x  Computer-Use  -  automating a system that has NO API",
        ha="center", va="center", fontsize=11.5, color=BLUE)

# ---- human goal -------------------------------------------------------------
box(31, 86.5, 38, 6, "Enterprise Architect  -  sets the goal\n"
    "\"Extract all Q3 manifests -> normalize to Oracle 23ai -> migrate.\n"
    "Do not stop until the reconciliation report is clean.\"",
    fc=LBLUE, ec=BLUE, fs=9.2)

# ---- zones ------------------------------------------------------------------
zone(3, 20, 44, 60, "1 . LONG-HORIZON AUTONOMY  (endurance + resilience)", LBLUE, NAVY)
zone(53, 20, 44, 60, "2 . COMPUTER-USE  (unbounded GUI access)", LCYAN, CYAN)

# ---- LEFT: orchestrator -----------------------------------------------------
box(7, 69, 36, 8,
    "Long-Horizon Orchestrator\n(plain Python state machine)",
    fc="white", ec=NAVY, fs=10, bold=True)

# state machine chips
box(7, 60, 10.5, 5, "EXTRACT", fc=LGREEN, ec=GREEN, fs=8.5, bold=True)
box(19.7, 60, 11.5, 5, "NORMALIZE", fc=LGREEN, ec=GREEN, fs=8.5, bold=True)
box(33.5, 60, 9.5, 5, "DONE", fc=LGREEN, ec=GREEN, fs=8.5, bold=True)
arrow(17.5, 62.5, 19.7, 62.5, color=GREEN, lw=1.4)
arrow(31.2, 62.5, 33.5, 62.5, color=GREEN, lw=1.4)

# checkpoint store
box(7, 48, 36, 7,
    "Checkpoint  -  checkpoints/state.json\nphase . attempts . extracted_file . normalized_file",
    fc="white", ec=NAVY, fs=8.8)
arrow(25, 60, 25, 55.2, color=NAVY, lw=1.4,
      label="save / resume after every step", ly=57.6, fs=7.8)

# recover note
box(7, 39, 36, 6.2,
    "recover()  -  on timeout: log it, bump attempts,\nre-invoke the worker, continue where it left off",
    fc=LRED, ec=RED, tc=RED, fs=8.6)

# ---- RIGHT: computer-use ----------------------------------------------------
box(57, 69, 36, 8,
    "Computer-Use Worker\nClaude (vision)  +  tool-use actions",
    fc="white", ec=CYAN, fs=10, bold=True)

# perceive-decide-act cycle chips
box(57, 60, 11, 5, "perceive\n(screenshot)", fc="white", ec=BLUE, fs=7.6)
box(70.5, 60, 9, 5, "decide\n(Claude)", fc="white", ec=BLUE, fs=7.6)
box(82, 60, 11, 5, "act\n(click/type)", fc="white", ec=BLUE, fs=7.6)
arrow(68, 62.5, 70.5, 62.5, color=BLUE, lw=1.3)
arrow(79.5, 62.5, 82, 62.5, color=BLUE, lw=1.3)
arrow(87.5, 60, 62.5, 60, color=BLUE, lw=1.3, rad=-0.45,
      label="loop until task done", ly=57.4, fs=7.6)

# browser
box(57, 48, 36, 7,
    "Chromium  (Playwright)\nreal mouse + keyboard, screenshots",
    fc="white", ec=CYAN, fs=8.8)

# legacy GUI
box(57, 36, 36, 8,
    "LegacyForms GUI  (Flask)  -  NO API\nlogin  .  select quarter  .  run query  .  export CSV",
    fc="white", ec=GREY, fs=8.8, bold=True)

# session timeout injection
box(64.5, 27.5, 21, 5.5,
    "(!) injected: \"Session Timeout\"\n(fires mid-export, once)",
    fc=LRED, ec=RED, tc=RED, fs=8.2, bold=True)

# ---- BOTTOM: coder + output -------------------------------------------------
box(18, 7, 28, 8,
    "Coder Agent\nnormalize legacy CSV -> 23ai schema\n(DD-MON-YY -> ISO, rename cols)",
    fc="white", ec=NAVY, fs=8.6)
box(55, 7, 30, 8,
    "Output\noutput/manifests_23ai.csv\n+ reconciliation report",
    fc=LGREEN, ec=GREEN, tc=GREEN, fs=8.8, bold=True)

# ---- cross arrows -----------------------------------------------------------
arrow(40, 86.5, 30, 77.4, color=BLUE, lw=2, label="goal", lx=37, ly=82.5)
arrow(43, 73, 57, 73, color=NAVY, lw=2.2,
      label="delegate EXTRACT task", ly=75.2, fs=8.2)
arrow(75, 60, 75, 55.2, color=CYAN, lw=1.6)
arrow(75, 48, 75, 44.2, color=CYAN, lw=1.6,
      label="HTTP / clicks", lx=83, ly=46, fs=7.6)
arrow(74, 36, 74, 33.2, color=RED, lw=1.6, ls="-")
arrow(75, 27.5, 94.5, 60, color=RED, lw=1.6, ls=(0, (4, 3)), rad=-0.5,
      label="worker reports\nstatus = timeout", lx=95.5, ly=44, lcolor=RED, fs=7.6)
arrow(57, 70, 43, 42.5, color=RED, lw=1.8, ls=(0, (5, 3)), rad=0.25,
      label="timeout\nbubbles up", lx=49.5, ly=58, lcolor=RED, fs=7.6)
arrow(63, 36, 40, 15.2, color=NAVY, lw=1.8, rad=0.15,
      label="exported\nlegacy CSV", lx=50, ly=27, fs=7.8)
arrow(25, 60, 25, 15.2, color=GREEN, lw=1.4, ls=(0, (4, 3)), rad=0.0,
      label="NORMALIZE\nphase", lx=14.5, ly=30, lcolor=GREEN, fs=7.6)
arrow(46, 11, 55, 11, color=GREEN, lw=2)

# ---- legend -----------------------------------------------------------------
legend = [
    Line2D([0], [0], color=NAVY, lw=2, label="control / data flow"),
    Line2D([0], [0], color=RED, lw=2, ls=(0, (5, 3)), label="failure & recovery path"),
    Line2D([0], [0], color=GREEN, lw=2, label="successful migration output"),
]
ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(0.012, 0.005),
          fontsize=8.5, frameon=True, facecolor="white", edgecolor=GREY)

plt.tight_layout()
out = "architecture.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print("wrote", out)
