"""Prueba la interfaz contra un servidor ya iniciado en localhost:8000."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests/fixtures/manifest.json").read_text())


def run():
    output = ROOT / "docs"
    failures = []
    checks = []
    with sync_playwright() as p:
        executable = os.environ.get("CHROME_PATH")
        browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda e: failures.append(str(e)))
        page.goto(os.environ.get("BASE_URL", "http://127.0.0.1:8000"))
        expect(page.locator(".cell")).to_have_count(81)
        variants = ["normal", "perspectiva", "sombra", "giro_90", "ruido_jpeg"]
        for puzzle, variant in zip(MANIFEST, variants):
            page.locator("#image").set_input_files(str(ROOT / "tests/fixtures" / puzzle["images"][variant]))
            page.locator("#read").click()
            expect(page.locator("#read")).to_be_enabled(timeout=60000)
            expect(page.locator("#clue-count")).to_have_text("32 pistas")
            expect(page.locator("#solve")).to_be_enabled()
            actual = page.locator(".cell").evaluate_all("(els) => els.map(e => Number(e.value))")
            assert actual == sum(puzzle["board"], []), (puzzle["id"], variant, actual)
            page.locator("#solve").click()
            expect(page.locator("#status")).to_have_class("status success", timeout=10000)
            actual = page.locator(".cell").evaluate_all("(els) => els.map(e => Number(e.value))")
            assert actual == sum(puzzle["solution"], [])
            expect(page.locator(".cell.calculated")).to_have_count(49)
            expect(page.locator("#solve")).to_be_disabled()
            if puzzle["id"] == 1:
                page.screenshot(path=str(output / "demo-desktop.png"), full_page=True)
            page.locator("#edit").click()
            assert page.locator(".cell").evaluate_all("(els) => els.map(e => Number(e.value))") == sum(puzzle["board"], [])
            checks.append({"sudoku": puzzle["id"], "variant": variant, "uploaded_and_solved": True})
        page.locator("#manual").click()
        expect(page.locator("#read")).to_be_disabled()
        page.locator(".cell").nth(0).fill("1")
        page.locator(".cell").nth(1).fill("1")
        page.locator("#solve").click()
        expect(page.locator("#status")).to_contain_text("repetidos")
        expect(page.locator(".cell.conflict")).to_have_count(2)
        page.locator(".cell").nth(1).fill("2")
        expect(page.locator("#confirmed")).to_have_count(0)
        expect(page.locator("#solve")).to_be_enabled()
        page.locator("#reset").click()
        expect(page.locator("#clue-count")).to_have_text("0 pistas")
        page.locator("#image").set_input_files(str(ROOT / "tests/fixtures/sudoku-1-muy_pequeno_144.png"))
        page.locator("#read").click()
        expect(page.locator("#status")).to_contain_text("pequeña", timeout=10000)
        expect(page.locator("#solve")).to_be_disabled()
        page.locator("#reset").click()
        page.get_by_role("button", name="Ejemplo 1", exact=True).click()
        expect(page.locator("#read")).to_be_enabled(timeout=60000)
        expect(page.locator("#clue-count")).to_have_text("32 pistas")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(output / "demo-mobile.png"), full_page=True)
        assert not failures, failures
        browser.close()
    (output / "browser-check.json").write_text(json.dumps({
        "cases": checks, "mobile_width": 390, "horizontal_overflow": False,
        "checks": ["solve_without_checkbox", "edit_restores_clues", "conflict_feedback",
                   "editing_keeps_solve_available", "reset", "tiny_image_rejected", "example_button"],
        "javascript_errors": failures
    }, indent=2), encoding="utf-8")
    print("Navegador: 5 subidas y soluciones correctas, controles y vista móvil comprobados.")


if __name__ == "__main__":
    run()
