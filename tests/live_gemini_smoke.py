"""Live Gemini smoke test. Explicit synthetic prompts only; no shared database writes."""
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chatbot_server as app

def main():
    try:
        _, model = app.model_config()
    except app.ConfigError:
        print("NOT RUN: Gemini API key or model configuration missing.", file=sys.stderr)
        return 2
    fixtures = [
        ("실직 후 긴급복지지원 신청에 필요한 서류는 무엇인가요?", "", "docs", "s1"),
        ("어머니의 노인장기요양 대리 신청에 필요한 위임 서류를 알려주세요.", "", "proxy", "s2"),
        ("유족연금 신청은 어떻게 하나요?", "", "apply", "s3"),
    ]
    passed = 0
    for i, (q, current, intent, pid) in enumerate(fixtures, 1):
        try:
            route = app.classify(q, current)
            if route != {"intent": intent, "pid": pid}:
                print(f"FAIL fixture {i}: expected {intent}/{pid}, got {route['intent']}/{route['pid']}")
                continue
            print(f"PASS fixture {i}: {route['intent']}/{route['pid']}")
            passed += 1
        except HTTPError as exc:
            print(f"FAIL fixture {i}: HTTP {exc.code}")
        except URLError:
            print(f"FAIL fixture {i}: network error")
        except (ValueError, KeyError, IndexError, TypeError, OSError):
            print(f"FAIL fixture {i}: invalid response or transport error")
    print(f"LIVE Gemini ({model}): {passed}/{len(fixtures)} correct routes")
    return 0 if passed == len(fixtures) else 1

if __name__ == "__main__":
    raise SystemExit(main())
