"""
WorldGuessr - Konum Yakalayıcı
 
"""

import asyncio
import json
import re
import os
from playwright.async_api import async_playwright

last_coords = None

def extract_json(text):
    text = text.strip()
    for prefix in [")]}'\n", ")]}'", ")]}'"]:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    match = re.search(r'\(\s*(\[.*)', text, re.DOTALL)
    if match:
        body = match.group(1).strip()
        if body.endswith(");"):
            body = body[:-2]
        elif body.endswith(")"):
            body = body[:-1]
        return body.strip()
    return text

def find_coords(obj, depth=0):
    if depth > 15:
        return None
    if isinstance(obj, list):
        if (len(obj) == 4 and obj[0] is None and obj[1] is None
                and isinstance(obj[2], float) and isinstance(obj[3], float)
                and -90 <= obj[2] <= 90 and -180 <= obj[3] <= 180):
            return obj[2], obj[3]
        for item in obj:
            r = find_coords(item, depth + 1)
            if r:
                return r
    return None

def find_country(obj, depth=0):
    if depth > 15:
        return None
    if isinstance(obj, str) and len(obj) == 2 and obj.isupper():
        return obj
    if isinstance(obj, list):
        for item in obj:
            r = find_country(item, depth + 1)
            if r:
                return r
    return None

def find_addresses(obj, depth=0):
    results = []
    if depth > 15:
        return results
    if (isinstance(obj, list) and len(obj) == 2
            and isinstance(obj[0], str) and isinstance(obj[1], str)
            and len(obj[1]) <= 3 and obj[0] not in ["", " "]):
        results.append(obj[0])
        return results
    if isinstance(obj, list):
        for item in obj:
            results.extend(find_addresses(item, depth + 1))
    return list(dict.fromkeys(results))

# Sayfa yüklenmeden önce çalışır.
# window.L setter ile bekliyoruz — L set edilir edilmez prototype'ı hookla.
# window.L.map override DEĞİL — o modül referansını değiştirmez.
# L.Map.prototype.initialize override + addInitHook → ikisi de shared, çalışır.
INIT_SCRIPT = """
(function() {
    function hookLeaflet(L) {
        if (!L || !L.Map) return false;
        if (L.__hunterHooked) return true;
        L.__hunterHooked = true;

        // Yöntem 1: addInitHook — map oluşturulurken çağrılır
        try {
            L.Map.addInitHook(function() {
                window.__leafletMap = this;
                console.log('[Hunter] addInitHook: map yakalandı!');
            });
        } catch(e) {}

        // Yöntem 2: prototype.initialize override
        try {
            var origInit = L.Map.prototype.initialize;
            L.Map.prototype.initialize = function(id, options) {
                var r = origInit.call(this, id, options);
                window.__leafletMap = this;
                console.log('[Hunter] prototype.initialize: map yakalandı!');
                return r;
            };
        } catch(e) {}

        console.log('[Hunter] Leaflet hooked!');
        return true;
    }

    // L zaten yüklüyse direkt hook'la
    if (window.L) {
        hookLeaflet(window.L);
        return;
    }

    // L henüz yüklenmediyse — setter ile bekle
    var _L = undefined;
    Object.defineProperty(window, 'L', {
        configurable: true,
        enumerable: true,
        get: function() { return _L; },
        set: function(val) {
            _L = val;
            console.log('[Hunter] window.L set edildi, hook kuruluyor...');
            hookLeaflet(val);
        }
    });
})();
"""

CLICK_JS = """
(function() {
    var lat = %s;
    var lng = %s;

    var map = window.__leafletMap;
    if (!map) return 'NO_MAP';

    var latlng = L.latLng(lat, lng);

    try {
        map.fire('click', {
            latlng: latlng,
            originalEvent: new MouseEvent('click', { bubbles: true })
        });
        console.log('[Hunter] click fired:', lat, lng);
        return 'OK';
    } catch(e) {
        return 'FIRE_ERR: ' + e.message;
    }
})();
"""

async def inject_click(page, lat, lng):
    js = CLICK_JS % (lat, lng)
    try:
        result = await page.evaluate(js)
        if result == "OK":
            print(f"  ✅ Tıklatıldı!")
            return True
        print(f"  ⚠️  Sonuç: {result}")
    except Exception as e:
        print(f"  ❌ Hata: {e}")
    return False

async def on_response(response, page):
    global last_coords
    if "GetMetadata" not in response.request.url:
        return
    try:
        text = await response.text()
        if not text.strip():
            return

        json_str = extract_json(text)
        data = json.loads(json_str)

        coords    = find_coords(data)
        country   = find_country(data) or "?"
        addresses = find_addresses(data)

        if not coords:
            return
        if coords == last_coords:
            return
        last_coords = coords

        lat, lng = coords
        label = addresses[0] if addresses else f"{lat:.4f}, {lng:.4f}"

        print("\n" + "═" * 52)
        print("  📍 KONUM YAKALANDI")
        print("═" * 52)
        print(f"  Koordinat : {lat:.6f}, {lng:.6f}")
        print(f"  Ülke      : {country}")
        print(f"  Adres     : {label}")
        print("═" * 52)

        await inject_click(page, lat, lng)

    except Exception:
        pass

async def main():
    print("""
╔══════════════════════════════════════════╗
║      WorldGuessr Hunter       ║
║       ║
╚══════════════════════════════════════════╝
Durdurmak için: Ctrl+C
""")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # Sayfa yüklenmeden önce hook'u kur
        await context.add_init_script(INIT_SCRIPT)

        page = await context.new_page()
        page.on("response", lambda res: asyncio.ensure_future(on_response(res, page)))

        await page.goto("https://worldguessr.com", wait_until="domcontentloaded")
        print("Tarayıcı açıldı. Oyunu başlat...\n")

        try:
            await page.wait_for_event("close", timeout=0)
        except Exception:
            pass

        await browser.close()

if __name__ == "__main__":
    os.environ.setdefault("DISPLAY", ":1")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDurduruldu.")
