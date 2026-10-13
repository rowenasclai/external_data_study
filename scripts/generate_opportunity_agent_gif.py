"""Render a compact animated Opportunity Agent workflow GIF using SVG + ffmpeg.

Requires ffmpeg built with the librsvg decoder. Run from repository root:
    python3 scripts/generate_opportunity_agent_gif.py
"""
import base64
from pathlib import Path
from xml.sax.saxutils import escape
import shutil
import subprocess

W, H = 1200, 675
OUT = Path("Result/Opportunity Agent/opportunity_agent_flow.gif")
LOGO = Path("assets/opportunity_agent/hsbc_logo_supplied.png")
# The repository's .runtime directory is gateway-owned; transient render frames
# intentionally live outside it.
WORK = Path("/tmp/opportunity_agent_gif_frames")

BG, PANEL, ACTIVE = "#D7D8D6", "#ECEDEB", "#FFFFFF"
TEXT, MUTED, LINE = "#17242E", "#46515A", "#9EA6A9"
GOLD, BLUE = "#A87C00", "#4587A7"
# Colour denotes workflow domain: external exploration (steps 1–2) is gold;
# internal handling (steps 3–4) is blue.
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
    return rect(x, y, width, 27, "#F8F9F7", color, 1, 13) + text(x + 12, y + 18, label, 10, color, 700)


def spark(cx, cy, radius, color):
    """Render a four-point spark to convey a hand-off between workflow stages."""
    inner = radius * 0.28
    points = [
        (cx, cy - radius), (cx + inner, cy - inner),
        (cx + radius, cy), (cx + inner, cy + inner),
        (cx, cy + radius), (cx - inner, cy + inner),
        (cx - radius, cy), (cx - inner, cy - inner),
    ]
    point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{point_string}" fill="{color}"/>'


def svg(active, progress):
    bits = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    bits += [rect(0, 0, W, H, BG)]
    # grid
    for x in range(0, W + 1, 48): bits.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#C9CAC8"/>')
    for y in range(0, H + 1, 48): bits.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#C9CAC8"/>')
    bits += [
        # Exact HSBC wordmark/device crop supplied by the user.
        f'<image href="{logo_data_uri()}" x="64" y="28" width="235" height="57" preserveAspectRatio="xMinYMid meet"/>',
        text(64, 108, "OPPORTUNITY AGENT", 18, TEXT, 700),
        text(64, 144, "From external signals to sales-ready prospects", 30, TEXT, 700),
        text(64, 170, "AUTOMATED MARKET INTELLIGENCE WORKFLOW", 12, MUTED, 700),
        text(64, 201, "EXTERNAL EXPLORATION", 13, GOLD, 700),
        f'<line x1="64" y1="214" x2="604" y2="214" stroke="{GOLD}" stroke-width="2"/>',
        text(631, 201, "INTERNAL HANDLING", 13, BLUE, 700),
        f'<line x1="631" y1="214" x2="1136" y2="214" stroke="{BLUE}" stroke-width="2"/>',
    ]
    card_w, card_h, gap, sx, cy = 250, 350, 25, 64, 230
    for i, (title, description, labels, color, icon) in enumerate(STAGES):
        x, on = sx + i * (card_w + gap), i == active
        bits.append(rect(x, cy, card_w, card_h, ACTIVE if on else PANEL, color if on else "#B7BCBC", 2 if on else 1, 20))
        if on:
            bits.append(rect(x + 1, cy + 1, card_w - 2, 6, color, "none", 0, 18))
        bits += [
            rect(x + 22, cy + 25, 45, 45, color, "none", 0, 12),
            text(x + 44, cy + 57, icon, 25, BG, 700, "middle"),
            text(x + 82, cy + 41, f"0{i + 1}", 12, MUTED, 700),
            text(x + 22, cy + 111, title, 22, TEXT, 700),
            text(x + 22, cy + 148, "BUSINESS LOGIC", 11, color, 700),
        ]
        for line_number, line in enumerate(description):
            bits.append(text(x + 22, cy + 177 + line_number * 18, line, 12, MUTED))
        for tag_number, label in enumerate(labels):
            bits.append(tag(x + 22, cy + 260 + tag_number * 31, label, color))
        if on:
            bits += [
                text(x + 22, cy + 329, "PROCESSING", 10, color, 700),
                rect(x + 109, cy + 323, 98, 6, "#BDC4C4", "none", 0, 3),
                rect(x + 109, cy + 323, int(98 * progress), 6, color, "none", 0, 3),
            ]
    # Spark hand-offs, deliberately after cards so they are visible in gaps.
    for i in range(3):
        x1, x2, yy = sx + i * (card_w + gap) + card_w + 8, sx + (i + 1) * (card_w + gap) - 15, cy + 170
        color = STAGES[i][4] if i < active else LINE
        bits.append(f'<line x1="{x1}" y1="{yy}" x2="{x2}" y2="{yy}" stroke="{color}" stroke-width="3" stroke-dasharray="6 6"/>')
        bits.append(spark(x2 + 3, yy, 9, color))
        if i == active - 1:
            moving_spark = x1 + int((x2 - x1 - 5) * progress)
            bits.append(spark(moving_spark, yy, 7, STAGES[i][4]))
    bits += [
        '<line x1="64" y1="599" x2="1136" y2="599" stroke="#9EA6A9"/>',
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
