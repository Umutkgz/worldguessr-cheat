<div align="center">

```
██╗    ██╗ ██████╗ ██████╗ ██╗     ██████╗  ██████╗ ██╗   ██╗███████╗███████╗███████╗██████╗
██║    ██║██╔═══██╗██╔══██╗██║     ██╔══██╗██╔════╝ ██║   ██║██╔════╝██╔════╝██╔════╝██╔══██╗
██║ █╗ ██║██║   ██║██████╔╝██║     ██║  ██║██║  ███╗██║   ██║█████╗  ███████╗███████╗██████╔╝
██║███╗██║██║   ██║██╔══██╗██║     ██║  ██║██║   ██║██║   ██║██╔══╝  ╚════██║╚════██║██╔══██╗
╚███╔███╔╝╚██████╔╝██║  ██║███████╗██████╔╝╚██████╔╝╚██████╔╝███████╗███████║███████║██║  ██║
 ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
                                                                        H U N T E R
```

**Automated geolocation extraction and map injection for WorldGuessr**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square)]()

*Intercepts Google Street View metadata in real time · Extracts GPS coordinates · Auto-clicks the correct map location*

</div>

---

## How It Works

WorldGuessr loads each round by calling Google's internal `GetMetadata` endpoint, which returns the exact GPS coordinates of the Street View location — before the user ever interacts with the map. This tool intercepts that response, parses the coordinates out of the nested JSON, and fires a synthetic click event on the Leaflet map at precisely the right location.

```
Browser opens worldguessr.com
        │
        ▼
Playwright listens to every HTTP response
        │
        ▼  (filters for GetMetadata only)
Google API response arrives  ──▶  strip XSSI prefix  ──▶  parse JSON
        │
        ▼  (recursive tree search)
Coordinates extracted: lat, lng, country, address
        │
        ▼
Injected JS fires map.fire('click', { latlng: L.latLng(lat, lng) })
        │
        ▼
Game registers correct guess ✓
```

No screen scraping. No pixel math. No OCR. The game hands us the answer.

---

## Features

- **Zero-latency extraction** — coordinates are captured at the network layer before Street View even finishes loading
- **Schema-agnostic parsing** — recursive pattern matching instead of hardcoded JSON paths; survives Google API format changes
- **XSSI-aware** — correctly strips Google's `)]}'\n` anti-abuse prefix before parsing
- **Pixel-independent clicking** — uses `L.LatLng` directly, so zoom level and map pan state are irrelevant
- **Pre-load JS hooking** — Leaflet's map object is captured via `Object.defineProperty` setter trap before any page scripts run
- **Dual hook strategy** — both `addInitHook` and `prototype.initialize` override for cross-version Leaflet compatibility
- **Deduplication** — prevents double-firing on repeated API calls for the same location
- **Bot-resistant launch** — suppresses `navigator.webdriver`, sets realistic User-Agent

---

## Requirements

- Python **3.10** or higher
- A working display (X11 on Linux, or standard desktop on macOS/Windows)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Umutkgz/worldguessr-cheat/
cd worldguessr-hunter
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
playwright>=1.40.0
```

### 4. Install Playwright's Chromium browser

```bash
playwright install chromium
```

> This downloads a standalone Chromium binary (~150 MB). It is isolated from your system Chrome and does not affect existing browser installations.

### 5. (Linux only) Install system dependencies

```bash
playwright install-deps chromium
```

> This installs shared libraries required by Chromium on Debian/Ubuntu-based systems (`libglib2.0`, `libnss3`, `libatk1.0`, etc.). Skip this step on macOS or Windows.

---

## Usage

```bash
python hunter.py
```

A Chromium window will open and navigate to `https://worldguessr.com`. Start a game normally — the script runs silently in the background and auto-clicks the correct location on the map as soon as each round loads.

**To stop:** Close the browser window, or press `Ctrl+C` in the terminal.

### What you'll see in the terminal

```
╔══════════════════════════════════════════╗
║         WorldGuessr Hunter               ║
╚══════════════════════════════════════════╝
Durdurmak için: Ctrl+C

════════════════════════════════════════════════════
  📍 KONUM YAKALANDI
════════════════════════════════════════════════════
  Koordinat : 41.015137, 28.979530
  Ülke      : TR
  Adres     : Sultanahmet, İstanbul
════════════════════════════════════════════════════
  ✅ Tıklatıldı!
```

---

## Running on a Headless Server (Linux)

If you are running this on a server without a physical display, you need a virtual framebuffer:

```bash
# Install Xvfb
sudo apt-get install xvfb

# Start a virtual display
Xvfb :1 -screen 0 1280x800x24 &

# Set DISPLAY and run
DISPLAY=:1 python hunter.py
```

The script sets `DISPLAY=:1` automatically as a fallback via `os.environ.setdefault`, but you still need Xvfb running beforehand.

---

## Project Structure

```
worldguessr-hunter/
├── hunter.py          # Main script
├── requirements.txt   # Python dependencies
├── README.md
└── LICENSE
```

### Key components inside `hunter.py`

| Component | Description |
|-----------|-------------|
| `extract_json()` | Strips Google's XSSI prefix (`)]}'`) from API responses before JSON parsing |
| `find_coords()` | Recursively searches nested JSON for the `[None, None, lat, lng]` coordinate signature |
| `find_country()` | Recursively finds ISO 3166-1 alpha-2 country codes (2-char uppercase strings) |
| `find_addresses()` | Collects all `[address_string, locale_code]` pairs found in the response tree |
| `INIT_SCRIPT` | JavaScript injected before page load; traps `window.L` assignment to hook Leaflet's map constructor |
| `CLICK_JS` | JavaScript template that fires a synthetic `click` event on the Leaflet map at given coordinates |
| `inject_click()` | Python wrapper that formats `CLICK_JS` with real coords and evaluates it via `page.evaluate()` |
| `on_response()` | Playwright response event handler; orchestrates the full extraction-and-click pipeline |
| `main()` | Launches browser with bot-mitigation flags, registers hooks, navigates to the game |

---

## Technical Notes

### Why `Object.defineProperty` for Leaflet?

Leaflet stores its map instances in module-local variables — not accessible from `window`. Instead of polling with `setInterval`, the script installs a property trap on `window.L` so that the moment Leaflet loads and assigns itself to the global, we intercept it synchronously and hook into `L.Map.prototype` before any page code runs.

### Why two hook methods?

`addInitHook` is Leaflet's official plugin API; `prototype.initialize` override is a lower-level fallback. Different Leaflet builds can behave differently across minor versions. Using both ensures at least one fires regardless of build.

### Why `L.LatLng` instead of pixel coordinates?

Converting GPS coordinates to screen pixels requires knowing the current map zoom level and center — both of which can change at any time. Providing `latlng` directly to `map.fire('click', ...)` bypasses this entirely; Leaflet's event system delivers geographic coordinates to handlers, not pixel positions.

### Why strip `)]}'\n`?

Google prefixes JSON responses from internal APIs with this string to prevent [XSSI attacks](https://security.stackexchange.com/questions/110539). A browser's `fetch()` call receives the full text and strips it before parsing. We replicate that step manually.

---

## Troubleshooting

**Browser opens but nothing happens**

The `GetMetadata` URL pattern may have changed. Open browser DevTools → Network tab, start a round, and look for requests to `maps.googleapis.com`. Update the URL filter string in `on_response()` if needed.

**`NO_MAP` appears in the terminal**

The Leaflet hook did not capture the map object in time. This can happen if the game's map initializes before `add_init_script` runs — unlikely but possible on very fast connections. Try adding a short `await asyncio.sleep(0.5)` before `page.goto()`.

**`ModuleNotFoundError: playwright`**

Make sure you activated your virtual environment before running the script:
```bash
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

**`Error: browserType.launch: Executable doesn't exist`**

Run `playwright install chromium` again. The browser binary may not have downloaded correctly.

**On Linux: `error while loading shared libraries`**

Run `playwright install-deps chromium` to install missing system libraries.

---

## Disclaimer

This project is intended for educational and research purposes — specifically to demonstrate browser automation, network interception, and JavaScript runtime hooking techniques. Use it responsibly. Running automation on online multiplayer games may violate those games' terms of service.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with [Playwright](https://playwright.dev/python/) · Powered by curiosity

</div>
