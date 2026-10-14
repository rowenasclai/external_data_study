"""Render a compact animated Opportunity Agent workflow GIF using SVG + ffmpeg.

Requires ffmpeg built with the librsvg decoder. Run from repository root:
    python3 scripts/generate_opportunity_agent_gif.py
"""
import base64
from math import pi, sin
from pathlib import Path
from xml.sax.saxutils import escape
import shutil
import subprocess

W, H = 1200, 675
OUT = Path("Result/Opportunity Agent/opportunity_agent_flow.gif")
# Exact serif wordmark + red device styling from the latest supplied reference,
# keyed to transparent background for placement on the animation canvas.
LOGO = Path("assets/opportunity_agent/hsbc_wordmark_reference_transparent.png")
# The repository's .runtime directory is gateway-owned; transient render frames
# intentionally live outside it.
WORK = Path("/tmp/opportunity_agent_gif_frames")

# Futuristic dark-mode palette: deep-space background, glass-like panels and
# high-energy gold/cyan signal colors. The HSBC logo stays on a light badge so
# the supplied black wordmark remains fully legible.
BG, PANEL, ACTIVE = "#071522", "#10243A", "#173C5E"
TEXT, MUTED, LINE = "#F4F7FB", "#AAB8C8", "#48637C"
GOLD, BLUE = "#F4B000", "#00A3E0"
# High-contrast colors reserved for the animated chevron hand-offs.
GOLD_ARROW, BLUE_ARROW = "#FFD166", "#00D9FF"
# Colour denotes workflow domain: external exploration (steps 1–2) is gold;
# internal handling (steps 3–4) is cyan.
STAGES = [
    ("Exploration", (
        "Scan external data sources",
        "(exhibitions, government",
        "contracts, trademarks) for",
        "specific external market",
        "information.",
    ), ("Gemini",), GOLD, "⌕"),
    ("Extraction", (
        "Parse unstructured text to",
        "identify key entities, dates, and",
        "the nature of the event and",
        "extract.",
    ), ("Hermes", "LLM (Llama 3.3 via Ollama)"), GOLD, "↧"),
    ("Matching", (
        "Reconcile extracted company",
        "names against internal CRMS",
        "databases or target lists.",
    ), ("GCP", "Fuzzy Matching / Embeddings"), BLUE, "≋"),
    ("Prospect list sharing", (
        "Format the matched opportunities",
        "into a prioritized list and",
        "distribute to the trade sales or",
        "front line.",
    ), ("Datastudio",), BLUE, "↗"),
]


def rect(x, y, w, h, fill, stroke="none", sw=1, radius=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def text(x, y, value, size, fill, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="DejaVu Sans, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


def logo_data_uri():
    """Embed the user-supplied HSBC logo crop into each SVG animation frame."""
    if not LOGO.is_file():
        raise FileNotFoundError(f"Required logo asset is missing: {LOGO}")
    payload = base64.b64encode(LOGO.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def tag(x, y, label, color):
    """Render exactly one technology tag in its own pill-shaped rectangle."""
    width = min(206, max(68, 20 + len(label) * 7.0))
    return rect(x, y, width, 27, "#0B1C2C", color, 1, 13) + text(x + 12, y + 18, label, 10, color, 700)


def chevron_right(cx, cy, size, color):
    """Render a scalable right-facing chevron used for animated hand-offs."""
    half = size / 2
    stroke = max(2, size * 0.24)
    return (
        f'<path d="M {cx - half:.1f} {cy - half:.1f} L {cx + half:.1f} {cy:.1f} '
        f'L {cx - half:.1f} {cy + half:.1f}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def arrow_accent(stage_index):
    """Use a sharper arrow color than the related card/icon accent."""
    return GOLD_ARROW if stage_index < 2 else BLUE_ARROW


def svg(active, progress):
    bits = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    bits += [rect(0, 0, W, H, BG)]
    bits += [
        # Exact serif HSBC wordmark/device styling, on transparent canvas.
        f'<image href="{logo_data_uri()}" x="64" y="28" width="160" height="57" preserveAspectRatio="xMinYMid meet"/>',
        text(64, 108, "OPPORTUNITY AGENT", 18, "#00D9FF", 700),
        text(64, 144, "From external signals to sales-ready prospects", 30, TEXT, 700),
        text(64, 170, "AUTOMATED MARKET INTELLIGENCE WORKFLOW", 12, MUTED, 700),
        text(64, 201, "EXTERNAL EXPLORATION", 13, GOLD, 700),
        f'<line x1="64" y1="214" x2="604" y2="214" stroke="{GOLD}" stroke-width="2"/>',
        text(631, 201, "INTERNAL HANDLING", 13, BLUE, 700),
        f'<line x1="631" y1="214" x2="1136" y2="214" stroke="{BLUE}" stroke-width="2"/>',
    ]
    # Wider inter-card gaps give the animated swipe arrows enough room to read.
    card_w, card_h, gap, sx, cy = 240, 350, 37, 64, 230
    for i, (title, description, labels, color, icon) in enumerate(STAGES):
        x, on = sx + i * (card_w + gap), i == active
        bits.append(rect(x, cy, card_w, card_h, ACTIVE if on else PANEL, color if on else "#294A68", 2 if on else 1, 20))
        if on:
            bits.append(rect(x + 1, cy + 1, card_w - 2, 6, color, "none", 0, 18))
        bits += [
            rect(x + 22, cy + 25, 45, 45, color, "none", 0, 12),
            text(x + 44, cy + 57, icon, 25, BG, 700, "middle"),
            text(x + 82, cy + 41, f"0{i + 1}", 12, MUTED, 700),
            text(x + 22, cy + 111, title, 20 if len(title) > 18 else 22, TEXT, 700),
            text(x + 22, cy + 148, "BUSINESS LOGIC", 11, color, 700),
        ]
        for line_number, line in enumerate(description):
            bits.append(text(x + 22, cy + 177 + line_number * 18, line, 12, MUTED))
        for tag_number, label in enumerate(labels):
            bits.append(tag(x + 22, cy + 260 + tag_number * 31, label, color))
        if on:
            bits += [
                text(x + 22, cy + 329, "PROCESSING", 10, color, 700),
                rect(x + 109, cy + 323, 98, 6, "#25445E", "none", 0, 3),
                rect(x + 109, cy + 323, int(98 * progress), 6, color, "none", 0, 3),
            ]
    # Chevron hand-offs, deliberately after cards so they are visible in gaps.
    # The active chevron moves right, expands at mid-transition, then contracts.
    for i in range(3):
        x1, x2, yy = sx + i * (card_w + gap) + card_w + 2, sx + (i + 1) * (card_w + gap) - 2, cy + 170
        color = arrow_accent(i) if i < active else LINE
        cx = (x1 + x2) / 2
        bits.append(f'<line x1="{x1}" y1="{yy}" x2="{x2}" y2="{yy}" stroke="{color}" stroke-width="1.5" stroke-linecap="round" opacity="0.55"/>')
        if i == active - 1:
            travel_start, travel_end = x1 + 8, x2 - 8
            moving_x = travel_start + (travel_end - travel_start) * progress
            # At the midpoint the chevron is largest; it returns to its normal
            # compact footprint when it reaches the receiving card.
            size = 9 + 14 * sin(pi * progress)
            bits.append(chevron_right(moving_x, yy, size, color))
        else:
            bits.append(chevron_right(cx, yy, 8, color))
    bits += [
        '<line x1="64" y1="599" x2="1136" y2="599" stroke="#48637C"/>',
        text(64, 630, "Explore  →  Extract  →  Match  →  Prioritize & Share", 16, TEXT, 700),
        text(1136, 630, f"STEP {active + 1} OF 4", 12, STAGES[active][4], 700, "end"),
        '</svg>',
    ]
    return "".join(bits)


def main():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to render the GIF")
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    frame_n = 0
    for active in range(4):
        for progress in (0.18, 0.48, 0.78, 1.0, 1.0):
            (WORK / f"frame{frame_n:03d}.svg").write_text(svg(active, progress), encoding="utf-8")
            frame_n += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    palette = WORK / "palette.png"
    base = ["ffmpeg", "-y", "-framerate", "5", "-i", str(WORK / "frame%03d.svg")]
    subprocess.run(base + ["-vf", "palettegen=max_colors=256", str(palette)], check=True)
    subprocess.run(base + ["-i", str(palette), "-lavfi", "paletteuse=dither=bayer", "-loop", "0", str(OUT)], check=True)
    print(f"Wrote {OUT} ({frame_n} frames at 5fps, {frame_n / 5:.1f}s)")


if __name__ == "__main__":
    main()
