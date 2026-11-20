"""Actual Chromium smoke test; intercept all external APIs; no shared DB writes."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("https://**/rest/v1/**", lambda r: r.abort())
        page.route("http://127.0.0.1:8787/**", lambda r: r.abort())
        page.goto((ROOT / "index.html").as_uri())
        expect(page.locator("[data-act=botopen]")).to_be_visible()
        page.locator("[data-act=botopen]").click()
        expect(page.locator(".bot-panel")).to_be_visible()
        page.locator("#bot-in").fill("실직했는데 필요한 서류")
        page.locator("#bot-in").press("Enter")
        expect(page.locator(".bot-log")).to_contain_text("이직확인서")
        expect(page.locator(".bot-log")).to_contain_text("seed.sql")
        page.locator("#bot-in").fill("신청 상태")
        page.locator("[data-act=botsend]").click()
        expect(page.locator(".bot-log")).to_contain_text("조회할 수 없어요")
        page.locator("#bot-in").fill("노인 장기요양 대리 신청")
        page.locator("#bot-in").press("Enter")
        expect(page.locator(".bot-log")).to_contain_text("대리신청 위임장")
        page.locator("#bot-in").fill("문자로 보내줘")
        page.locator("[data-act=botsend]").click()
        page.locator(".bchips [data-v='sms:s2']").last.click()
        expect(page.locator(".bot-log")).to_contain_text("실제 전송 없음")
        page.screenshot(path=str(ROOT / "browser-chatbot-desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator(".bot-panel")).to_be_visible()
        assert page.locator(".bot-panel").bounding_box()["width"] <= 390
        page.screenshot(path=str(ROOT / "browser-chatbot-mobile.png"))
        page.locator(".bot-panel [data-act=botclose]").click()
        expect(page.locator(".bot-panel")).to_have_count(0)
        assert not errors, errors
        browser.close()
        print("PASS: real Chromium, offline chatbot interaction, mobile layout, zero JS errors")

if __name__ == "__main__":
    run()
