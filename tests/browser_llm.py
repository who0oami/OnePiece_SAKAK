"""Real Chromium, local static server + mocked Gemini routing response."""
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
def run():
    env={**os.environ,"CHATBOT_PORT":"18000","GEMINI_API_KEY":"","GEMINI_MODEL":""}
    proc=subprocess.Popen([sys.executable,"chatbot_server.py"],cwd=ROOT,env=env)
    try:
        for _ in range(30):
            try:
                with urlopen("http://127.0.0.1:18000/api/chat/health",timeout=1) as response:
                    assert response.status==200
                break
            except OSError:
                time.sleep(.15)
        else:
            raise RuntimeError("server did not start")
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page(viewport={"width":1280,"height":900})
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.route("https://**/rest/v1/**",lambda r:r.abort())
            page.route("http://127.0.0.1:8787/**",lambda r:r.abort())
            requests=[]
            def mock(route):
                requests.append(route.request.post_data_json)
                route.fulfill(status=200,json={"mode":"gemini","intent":"docs","pid":"s2"})
            page.route("**/api/chat",mock)
            page.goto("http://127.0.0.1:18000/")
            page.locator("[data-act=botopen]").click()
            page.locator("[data-act=botllm]").click()
            page.locator("#bot-in").fill("어머니가 거동이 불편하셔서 도움을 받고 싶어요")
            page.locator("#bot-in").press("Enter")
            expect(page.locator(".bot-log")).to_contain_text("AI 질문 분류 완료")
            expect(page.locator(".bot-log")).to_contain_text("의사소견서")
            assert len(requests)==1 and set(requests[0])=={"question","current_pid"}
            page.locator("#bot-in").fill("010-1234-5678")
            page.locator("#bot-in").press("Enter")
            expect(page.locator(".bot-log")).to_contain_text("개인정보 포함 가능 질문")
            assert len(requests)==1
            page.locator("#bot-in").fill("진행 상태")
            page.locator("#bot-in").press("Enter")
            expect(page.locator(".bot-log")).to_contain_text("조회할 수 없어요")
            assert len(requests)==1
            page.unroute("**/api/chat")
            # Actual local backend HTTP path, deliberately no key; must fall back.
            page.locator("#bot-in").fill("실직했는데 필요한 서류")
            page.locator("#bot-in").press("Enter")
            expect(page.locator(".bot-log")).to_contain_text("기존 시연 안내로 전환")
            expect(page.locator(".bot-log")).to_contain_text("이직확인서")
            assert not errors,errors
            page.screenshot(path=str(ROOT/"browser-chatbot-llm.png"))
            browser.close()
        print("PASS: real Chromium + local backend, mocked Gemini success and actual 503 fallback")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
if __name__=="__main__":
    run()
