#!/usr/bin/env python3
"""
render_visual.py — factcheck-flow visual renderer.

Turns a self-contained HTML file into a brand-consistent raster image and, optionally,
uploads it to the WordPress media library and prints the block-ready values.

The HTML you write only owns LAYOUT. This script owns the BRAND:
  * it injects the Pabau webfont (Satoshi, cached locally as base64 @font-face rules),
  * it injects the Pabau design tokens as CSS custom properties,
  * it renders at 2x for retina, on a fixed canvas so every visual on the blog shares
    the same widths,
  * it refuses to ship a visual whose content is clipped by the canvas edge.

Usage
-----
  # render only
  render_visual.py --html chart.html --preset standard --out chart.webp

  # render + upload, print {"id":…, "source_url":…} for the wp:image block
  render_visual.py --html chart.html --preset standard \
      --slug botox-unit-ranges-by-area \
      --alt "Bar chart of typical Botox unit ranges for glabella, forehead and crow's feet" \
      --upload

  # environment check (run this before you build anything)
  render_visual.py --check

  # lint an interactive (CSS-only) embed before pasting it into a wp:html block
  render_visual.py --lint-embed embed.html

Exit codes: 0 ok, 1 usage/render/lint failure, 2 environment missing.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

FF = Path(os.environ.get("FF_HOME", Path.home() / ".claude" / "factcheck-flow"))
CACHE = FF / "cache" / "fonts"

# --------------------------------------------------------------------------------------
# Brand
# --------------------------------------------------------------------------------------
# Every value below is lifted from what is live on pabau.com — the Elementor kit's font
# stack and the pabau-provider-card stylesheet. Do not "improve" these: a visual is on
# brand because it uses the same tokens as the rest of the page, not because it looks nice
# on its own.

FONT_BASE = "https://pabau.com/wp-content/uploads/2022/08"
# (filename, css weight, css style) — the site's own @font-face weights are idiosyncratic
# (Medium is mapped to 200); these are remapped to conventional CSS weights so the HTML
# you write can use normal numbers.
FONTS = [
    ("Satoshi-Light.woff2", 300, "normal"),
    ("Satoshi-Regular.woff2", 400, "normal"),
    ("Satoshi-Italic.woff2", 400, "italic"),
    ("Satoshi-Medium.woff2", 500, "normal"),
    ("Satoshi-Bold.woff2", 700, "normal"),
]

TOKENS = {
    # text
    "--pb-ink": "#121D36",        # headings, big numbers
    "--pb-body": "#3D4757",       # body copy
    "--pb-muted": "#8A94A6",      # labels, axis ticks, footnotes
    # brand
    "--pb-blue": "#037CD2",       # primary — links, primary series, CTA
    "--pb-cyan": "#24BEE1",       # accent — highlights, bullets, top-pick rule
    "--pb-navy": "#1A2539",       # deep fill
    # surfaces
    "--pb-page": "#FFFFFF",
    "--pb-surface": "#F5F8FB",    # tinted panel
    "--pb-tint": "#E4F7FC",       # cyan wash (pill backgrounds)
    "--pb-line": "#E3E8EF",       # borders, gridlines
    "--pb-track": "#DDE3EC",      # empty half of a bar/meter track
    # semantic (never hue-only — always paired with a glyph or a label)
    "--pb-pro": "#16794C",
    "--pb-con": "#A8412B",
    "--pb-warn": "#F0A32B",
    # gradient used by the download box, reused for hero panels
    "--pb-wash-a": "#E2F2FD",
    "--pb-wash-b": "#DFE3FD",
    # elevation
    "--pb-shadow": "0 1px 2px rgba(18,29,54,.05), 0 10px 28px -8px rgba(18,29,54,.16)",
    "--pb-radius": "14px",
}

# Categorical series order. Blue-to-cyan-to-navy, deliberately NOT red/green: the ramp
# stays legible for red-green colour vision deficiency, and adjacent series differ in
# lightness as well as hue so they survive greyscale printing too.
SERIES = ["#037CD2", "#24BEE1", "#1A2539", "#6BA9D8", "#0B6F86", "#9BB4CC"]

# Fixed canvases. Width is always 1200 logical px (the blog renders body images at 800px,
# so 1200 @2x downsamples to something crisp). Pick by content shape, never by eye.
PRESETS = {
    "wide": (1200, 675),       # hero, 16:9 — one chart, few categories
    "standard": (1200, 800),   # the default — chart plus a note, or a 2-up
    "tall": (1200, 1100),      # ranked bars, many rows, a stacked comparison
    "square": (1000, 1000),    # single donut/meter, social-friendly
    "strip": (1200, 420),      # a timeline, a stat row, a single meter
}

CHROME_CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "microsoft-edge",
]


def die(msg: str, code: int = 1):
    print(f"render_visual: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------------------
# Environment
# --------------------------------------------------------------------------------------

def find_chrome() -> str | None:
    env = os.environ.get("CHROME_BIN")
    if env and (shutil.which(env) or Path(env).exists()):
        return env
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        w = shutil.which(c)
        if w:
            return w
    return None


def have_pil() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def font_css(offline_ok: bool = True) -> str:
    """@font-face rules with the woff2 payload inlined as base64.

    Cached under $FF/cache/fonts so the download happens once per machine. If a font is
    unavailable (offline, first run behind a proxy) we fall back to the system stack —
    the visual still renders, it just isn't in the brand face, and we say so on stderr.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    rules, missing = [], []
    for name, weight, style in FONTS:
        p = CACHE / name
        if not p.exists():
            try:
                req = urllib.request.Request(
                    f"{FONT_BASE}/{name}",
                    headers={"User-Agent": "Mozilla/5.0 (factcheck-flow render_visual)"},
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = r.read()
                if not data:
                    raise ValueError("empty")
                p.write_bytes(data)
            except Exception:
                missing.append(name)
                continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        rules.append(
            "@font-face{font-family:'Satoshi';font-style:%s;font-weight:%d;"
            "font-display:block;src:url(data:font/woff2;base64,%s) format('woff2')}"
            % (style, weight, b64)
        )
    if missing and not rules:
        if not offline_ok:
            die("could not fetch the Satoshi webfont and --require-font was set", 2)
        print(
            "render_visual: WARNING Satoshi unavailable, falling back to the system font "
            "stack. The visual will render but will not be in the brand face.",
            file=sys.stderr,
        )
    elif missing:
        print(f"render_visual: note — missing font weights: {', '.join(missing)}", file=sys.stderr)
    return "".join(rules)


# --------------------------------------------------------------------------------------
# HTML assembly
# --------------------------------------------------------------------------------------

EXTERNAL_RE = re.compile(r"""(?:src|href)\s*=\s*['"](?!data:|#)(https?:)?//""", re.I)

BASE_CSS = """
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--pb-page)}
body{
  font-family:'Satoshi',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  color:var(--pb-body);
  -webkit-font-smoothing:antialiased;
  font-variant-numeric:tabular-nums;
  font-feature-settings:'tnum' 1;
}
#pv-frame{
  width:var(--pv-w);padding:var(--pv-pad);
  background:var(--pb-page);
  overflow:hidden;
}
#pv-canvas{
  width:100%;height:var(--pv-h);
  overflow:hidden;position:relative;
  background:var(--pb-page);
}
h1,h2,h3,h4{margin:0;color:var(--pb-ink);font-weight:700;letter-spacing:-.02em;line-height:1.15}
p{margin:0}
/* the numbers in a chart are the point — keep them tabular and tight */
.pv-num{font-variant-numeric:tabular-nums;letter-spacing:-.02em;color:var(--pb-ink);font-weight:700}
.pv-label{font-size:13px;color:var(--pb-muted)}
.pv-kicker{font-size:11.5px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;color:var(--pb-muted)}
.pv-source{font-size:12px;color:var(--pb-muted)}
.pv-rule{height:1px;background:var(--pb-line);border:0;margin:0}
"""


MEASURE_JS = (
    "<script>window.addEventListener('load',function(){"
    "var c=document.getElementById('pv-canvas');"
    "document.title='PVH:'+Math.ceil(c.getBoundingClientRect().height);});</script>"
)


def build_page(body_html: str, w: int, h: int | None, fonts: str,
               measure: bool = False, pad: int = 0) -> str:
    token_css = ";".join(f"{k}:{v}" for k, v in TOKENS.items())
    series_css = ";".join(f"--pb-series-{i+1}:{c}" for i, c in enumerate(SERIES))
    height = "auto" if h is None else f"{h}px"
    # A full document the author's fragment is dropped into. If the author already supplied
    # a full document we still wrap it — Chrome tolerates the nesting and the tokens win.
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>pv</title><style>"
        f"{fonts}"
        f":root{{{token_css};{series_css};--pv-w:{w - 2 * pad}px;--pv-h:{height};"
        f"--pv-pad:{pad}px}}"
        f"{BASE_CSS}"
        "</style></head><body>"
        f"<div id='pv-frame'><div id='pv-canvas'>{body_html}</div></div>"
        f"{MEASURE_JS if measure else ''}"
        "</body></html>"
    )


def strip_wrapper(src: str) -> str:
    """Accept either a fragment or a whole document; return the part that is the visual."""
    m = re.search(r"<body[^>]*>(.*)</body>", src, re.S | re.I)
    if m:
        src = m.group(1)
    # Hoist any author <style> so it survives the wrap (it does anyway, but keep it tidy).
    return src.strip()


# --------------------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------------------

def screenshot(chrome: str, page_html: str, w: int, h: int, scale: int, out_png: Path):
    with tempfile.TemporaryDirectory(prefix="pv-") as td:
        src = Path(td) / "visual.html"
        src.write_text(page_html, encoding="utf-8")
        profile = Path(td) / "profile"
        cmd = [
            chrome, "--headless", "--disable-gpu", "--no-sandbox",
            "--no-first-run", "--no-default-browser-check",
            "--hide-scrollbars", "--disable-extensions",
            "--disable-lcd-text",                     # crisper text when downscaled
            "--default-background-color=00000000",
            f"--user-data-dir={profile}",
            f"--force-device-scale-factor={scale}",
            f"--window-size={w},{h}",
            f"--screenshot={out_png}",
            src.as_uri(),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            die("Chrome timed out rendering the visual. Is the HTML fetching something "
                "off the network? Visuals must be fully self-contained.")
        if not out_png.exists() or out_png.stat().st_size == 0:
            tail = (r.stderr or b"").decode("utf-8", "replace")[-800:]
            die(f"Chrome produced no image.\n{tail}")


def measure_height(chrome: str, page_html: str, w: int, max_h: int) -> int | None:
    """Ask Chrome how tall the canvas actually is when its height is `auto`.

    Used by --fit so a visual is exactly as tall as its content, instead of floating in
    the dead space of a preset that was a size too big. --dump-dom runs the page's
    scripts, so the measuring script can hand the number back through the title.
    """
    with tempfile.TemporaryDirectory(prefix="pv-m-") as td:
        src = Path(td) / "measure.html"
        src.write_text(page_html, encoding="utf-8")
        cmd = [
            chrome, "--headless", "--disable-gpu", "--no-sandbox",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            f"--user-data-dir={Path(td) / 'profile'}",
            f"--window-size={w},{max_h}",
            "--virtual-time-budget=3000",
            "--dump-dom", src.as_uri(),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            return None
    m = re.search(rb"PVH:(\d+)", r.stdout or b"")
    if not m:
        return None
    got = int(m.group(1))
    return got if 40 <= got <= max_h else None


def check_fit(png: Path, w: int, h: int, scale: int) -> list[str]:
    """Flag content that runs into the canvas edge — i.e. a visual that got cut off.

    We sample the outermost pixel ring. A correctly composed visual has a margin, so that
    ring is uniform background. Ink in it means the layout overflowed and the screenshot
    silently cropped it, which is the single most common way a generated chart ships broken.
    """
    if not have_pil():
        return []
    from PIL import Image
    from collections import Counter
    im = Image.open(png).convert("RGB")
    W, H = im.size
    inset = max(1, scale)          # skip the very outermost row (AA fringe)

    def mixed(pixels: list[tuple]) -> bool:
        """True when the edge line is patchy rather than uniform.

        A deliberately full-bleed visual (a coloured panel running to the border) gives a
        UNIFORM edge line — that is fine and common. Content that got cut off by the
        screenshot gives a PATCHY one: bars alternating with gaps, or the top halves of
        clipped letters. So uniformity, not the presence of ink, is the test.
        """
        if not pixels:
            return False
        modal = Counter(pixels).most_common(1)[0][0]
        off = sum(1 for p in pixels
                  if max(abs(a - b) for a, b in zip(p, modal)) > 12)
        return off > max(2, len(pixels) * 0.02)

    step_x, step_y = max(1, W // 400), max(1, H // 400)
    edges = {
        "bottom": [im.getpixel((x, H - 1 - inset)) for x in range(inset, W - inset, step_x)],
        "right": [im.getpixel((W - 1 - inset, y)) for y in range(inset, H - inset, step_y)],
        "top": [im.getpixel((x, inset)) for x in range(inset, W - inset, step_x)],
    }
    return [side for side, px in edges.items() if mixed(px)]


def to_webp(png: Path, out: Path, quality: int) -> Path:
    if not have_pil():
        if out.suffix.lower() == ".webp":
            print("render_visual: note — Pillow not installed, shipping PNG instead of WebP "
                  "(pip install pillow for smaller files).", file=sys.stderr)
            out = out.with_suffix(".png")
        shutil.copyfile(png, out)
        return out
    from PIL import Image
    im = Image.open(png).convert("RGB")
    if out.suffix.lower() == ".webp":
        im.save(out, "WEBP", quality=quality, method=6)
    else:
        im.save(out, optimize=True)
    return out


# --------------------------------------------------------------------------------------
# WordPress upload
# --------------------------------------------------------------------------------------

def wp_creds() -> tuple[str, str, str]:
    base = os.environ.get("WP_BASE_URL", "")
    user = os.environ.get("WP_USER", "")
    pw = os.environ.get("WP_APP_PASSWORD", "")
    if base and user and pw:
        return base.rstrip("/"), user, pw
    path = Path(os.environ.get("WP_CREDENTIALS_FILE") or (FF / "wp-credentials"))
    if not path.exists():
        die("no WordPress credentials (set WP_BASE_URL/WP_USER/WP_APP_PASSWORD, "
            "$WP_CREDENTIALS_FILE, or ~/.claude/factcheck-flow/wp-credentials)", 2)
    txt = path.read_text(encoding="utf-8", errors="replace")
    def grab(*keys):
        # Tolerates the labelled-document shape the installer writes, including markdown
        # list bullets and bold labels: "- Site URL: …", "**Username:** …", "WP_USER=…".
        for k in keys:
            m = re.search(
                rf"^[ \t]*(?:[-*+][ \t]*)?(?:\*\*)?{re.escape(k)}(?:\*\*)?[ \t]*[:=][ \t]*(.+?)[ \t]*$",
                txt, re.I | re.M)
            if m:
                return m.group(1).strip().strip('"').strip("'").strip("`")
        return ""
    base = base or grab("WP_BASE_URL", "Site URL", "Site")
    user = user or grab("WP_USER", "Username", "User")
    pw = pw or grab("WP_APP_PASSWORD", "Application Password", "App Password", "Password")
    if not (base and user and pw):
        die(f"credentials file {path} is missing one of site URL / username / app password", 2)
    return base.rstrip("/"), user, pw


def upload(img: Path, slug: str, alt: str, title: str) -> dict:
    base, user, pw = wp_creds()
    mime = {"webp": "image/webp", "png": "image/png", "jpg": "image/jpeg",
            "jpeg": "image/jpeg"}[img.suffix.lower().lstrip(".")]
    fname = f"{slug}{img.suffix.lower()}"
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(
        f"{base}/wp-json/wp/v2/media",
        data=img.read_bytes(),
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": mime,
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (factcheck-flow render_visual)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            created = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        die(f"media upload failed: HTTP {e.code} {e.read()[:400].decode('utf-8','replace')}")
    except urllib.error.URLError as e:
        die(f"media upload failed: {e.reason}")

    mid = created.get("id")
    # Second call: alt text and title are not settable on the binary POST.
    if mid and (alt or title):
        body = json.dumps({k: v for k, v in
                           (("alt_text", alt), ("title", title)) if v}).encode()
        patch = urllib.request.Request(
            f"{base}/wp-json/wp/v2/media/{mid}", data=body, method="POST",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0 (factcheck-flow render_visual)"},
        )
        try:
            with urllib.request.urlopen(patch, timeout=60) as r:
                created = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"render_visual: WARNING uploaded but could not set alt text ({e}). "
                  f"Set it on media {mid} before you ship.", file=sys.stderr)
    return {
        "id": mid,
        "source_url": created.get("source_url"),
        "alt_text": (created.get("alt_text") or alt),
        "mime_type": created.get("mime_type"),
    }


# --------------------------------------------------------------------------------------
# Interactive-embed lint
# --------------------------------------------------------------------------------------

def lint_embed(path: Path) -> int:
    """Check a CSS-only interactive visualization before it goes into a wp:html block."""
    src = path.read_text(encoding="utf-8", errors="replace")
    problems, notes = [], []

    if re.search(r"<script\b", src, re.I):
        problems.append(
            "contains <script>. Interactive visuals must be CSS-only: WP Rocket defers and "
            "delays JavaScript, so an inline script is not reliably executed on the live page.")
    if re.search(r"\son[a-z]+\s*=", src, re.I):
        problems.append("has an inline event handler (onclick=…). CSS-only, so no handlers.")
    for m in EXTERNAL_RE.finditer(src):
        problems.append(f"loads an external resource near offset {m.start()}. "
                        "Everything must be inline — no CDN, no remote font, no remote image.")
        break
    if not re.search(r"<style\b", src, re.I):
        notes.append("no <style> block found — check the styling is inline on the elements.")

    # Scoping: every selector in the <style> must be under one unique root class.
    classes = set(re.findall(r'class\s*=\s*["\']([^"\']+)', src))
    flat = {c for group in classes for c in group.split()}
    prefixes = {c.split("-")[0] for c in flat if "-" in c}
    if flat and not any(p == "pv" for p in prefixes):
        problems.append("classes are not namespaced. Every class must start `pv-` so the "
                        "embed cannot collide with theme or Elementor CSS.")
    for sel in re.findall(r"(?m)^\s*([.#][A-Za-z][^{,\n]*)\{", src):
        s = sel.strip()
        if not s.startswith((".pv-", "#pv-")):
            problems.append(f"unscoped selector `{s}` — prefix it with .pv-…")
            break
    for m in re.finditer(r"\[[A-Za-z_-]+[~^$*|]?=\s*([^\]\"'\s][^\]]*)\]", src):
        val = m.group(1).strip()
        if val and (val[0].isdigit() or not re.fullmatch(r"[A-Za-z_-][\w-]*", val)):
            problems.append(
                f"attribute selector [{m.group(0)[1:-1]}] has an UNQUOTED value that is not a "
                "valid CSS identifier, so the browser discards the whole rule and the visual "
                f'renders in its default state. Write it as ["{val}"].')
            break
    if re.search(r"(?m)^\s*(body|html|h[1-6]|p|ul|li|table|a)\s*[,{]", src):
        problems.append("styles a bare element selector, which leaks into the whole article. "
                        "Scope every rule under the .pv-… root.")
    if len(src) > 60000:
        notes.append(f"{len(src)} bytes is large for one block; consider a rendered image.")
    if not re.search(r"@media[^{]*max-width", src):
        problems.append("no mobile breakpoint. Over half of blog traffic is mobile — add a "
                        "`@media (max-width:640px)` rule that reflows the visual to one column.")

    tag = f"lint {path}"
    for n in notes:
        print(f"NOTE  {tag}: {n}")
    for p in problems:
        print(f"FAIL  {tag}: {p}")
    if problems:
        print(f"\n{len(problems)} problem(s). Fix them before pasting this into a wp:html block.")
        return 1
    print(f"PASS  {tag}: self-contained, scoped, CSS-only, responsive.")
    return 0


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def cmd_check() -> int:
    chrome = find_chrome()
    ok = True
    print(f"chrome        : {chrome or 'MISSING'}")
    if not chrome:
        print("                install Google Chrome or Chromium, or set $CHROME_BIN")
        ok = False
    print(f"pillow        : {'yes' if have_pil() else 'no (PNG only, no fit check)'}")
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = sorted(p.name for p in CACHE.glob("*.woff2"))
    print(f"satoshi cache : {len(cached)}/{len(FONTS)} weights {cached if cached else ''}")
    try:
        base, user, _ = wp_creds()
        print(f"wordpress     : {base} as {user}")
    except SystemExit:
        print("wordpress     : no credentials (rendering works, --upload will not)")
    print(f"presets       : {', '.join(f'{k} {v[0]}x{v[1]}' for k, v in PRESETS.items())}")
    return 0 if ok else 2


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", help="path to the visual's HTML (fragment or full document)")
    ap.add_argument("--out", help="output image path (default: alongside the HTML, .webp)")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="standard")
    ap.add_argument("--width", type=int, help="override the preset width (logical px)")
    ap.add_argument("--height", type=int, help="override the preset height (logical px)")
    ap.add_argument("--fit", action="store_true",
                    help="measure the content and crop the canvas to its real height "
                         "(use for content-flow layouts; not for height:100%% layouts)")
    ap.add_argument("--max-height", type=int, default=2600,
                    help="ceiling for --fit (default 2600 logical px)")
    ap.add_argument("--pad", type=int, default=0,
                    help="page-background padding around the canvas (logical px). Use it "
                         "when previewing a full-bleed design so the edge-clipping check "
                         "has background to compare against.")
    ap.add_argument("--scale", type=int, default=2, help="device pixel ratio (default 2)")
    ap.add_argument("--quality", type=int, default=88, help="WebP quality (default 88)")
    ap.add_argument("--format", choices=["webp", "png"], default="webp")
    ap.add_argument("--upload", action="store_true", help="upload to the WP media library")
    ap.add_argument("--slug", help="media filename slug, e.g. botox-units-by-area")
    ap.add_argument("--alt", default="", help="alt text (required with --upload)")
    ap.add_argument("--title", default="", help="media library title (defaults to the slug)")
    ap.add_argument("--require-font", action="store_true",
                    help="fail instead of falling back to the system font stack")
    ap.add_argument("--allow-clipped", action="store_true",
                    help="ship even if content touches the canvas edge (don't)")
    ap.add_argument("--check", action="store_true", help="print an environment report and exit")
    ap.add_argument("--lint-embed", metavar="FILE",
                    help="lint a CSS-only interactive embed instead of rendering")
    a = ap.parse_args()

    if a.check:
        return cmd_check()
    if a.lint_embed:
        p = Path(a.lint_embed).expanduser()
        if not p.exists():
            die(f"{p} not found")
        return lint_embed(p)
    if not a.html:
        ap.print_usage(sys.stderr)
        die("--html is required (or use --check / --lint-embed)")

    src_path = Path(a.html).expanduser()
    if not src_path.exists():
        die(f"{src_path} not found")

    chrome = find_chrome()
    if not chrome:
        die("no Chrome/Chromium found. Install Google Chrome or set $CHROME_BIN. "
            "Visuals are rendered locally by headless Chrome; there is no fallback.", 2)

    w, h = PRESETS[a.preset]
    w, h = (a.width or w), (a.height or h)

    body = strip_wrapper(src_path.read_text(encoding="utf-8", errors="replace"))
    if EXTERNAL_RE.search(body):
        print("render_visual: WARNING the HTML references an external URL. Chrome may "
              "block or stall on it — inline every asset as a data: URI.", file=sys.stderr)

    slug = a.slug or re.sub(r"[^a-z0-9]+", "-", src_path.stem.lower()).strip("-")
    out = Path(a.out).expanduser() if a.out else src_path.with_suffix("." + a.format)
    out.parent.mkdir(parents=True, exist_ok=True)

    fonts = font_css(offline_ok=not a.require_font)

    if a.fit and not a.height:
        measured = measure_height(
            chrome, build_page(body, w, None, fonts, measure=True, pad=a.pad),
            w, a.max_height)
        if measured:
            h = measured
        else:
            print("render_visual: note — could not measure the content, keeping the "
                  f"{a.preset} preset height.", file=sys.stderr)

    page = build_page(body, w, h, fonts, pad=a.pad)

    with tempfile.TemporaryDirectory(prefix="pv-out-") as td:
        raw = Path(td) / "raw.png"
        screenshot(chrome, page, w, h + 2 * a.pad, a.scale, raw)
        clipped = [] if a.allow_clipped else check_fit(raw, w, h + 2 * a.pad, a.scale)
        if clipped:
            die("content runs off the " + " and ".join(clipped) + " edge of the "
                f"{w}x{h} canvas, so the screenshot cut it off. Use a taller preset "
                f"(current: {a.preset}), reduce the content, or pass --height. "
                "Presets: " + ", ".join(f"{k}={v[0]}x{v[1]}" for k, v in PRESETS.items()))
        out = to_webp(raw, out, a.quality)

    size_kb = out.stat().st_size / 1024
    result = {
        "file": str(out),
        "canvas": f"{w}x{h}@{a.scale}x",
        "pixels": f"{w * a.scale}x{h * a.scale}",
        "kb": round(size_kb, 1),
    }
    if size_kb > 400:
        print(f"render_visual: note — {size_kb:.0f} KB is heavy for a blog image; "
              f"lower --quality or use a shorter preset.", file=sys.stderr)

    if a.upload:
        if not a.alt:
            die("--upload requires --alt. Alt text is not optional on a data visualization: "
                "it is how the figures reach a screen reader and a fact-checker.")
        result.update(upload(out, slug, a.alt, a.title or slug.replace("-", " ").capitalize()))

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
