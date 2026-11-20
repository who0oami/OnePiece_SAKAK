"""Live Gemini smoke test. Explicit synthetic prompts only; no shared database writes."""
import sys
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chatbot_server as app

def diagnose_http(exc):
    # Never print provider error bodies, request headers, or API keys.
    try:
        data = json.loads(exc.read(32768)).get("error", {})
        msg = str(data.get("message", "")).lower()
        status = str(data.get("status", ""))
        safe_status = status if status in ("INVALID_ARGUMENT","FAILED_PRECONDITION","PERMISSION_DENIED","UNAUTHENTICATED","NOT_FOUND","RESOURCE_EXHAUSTED","UNAVAILABLE","INTERNAL") else "UNKNOWN"
        reasons = set()
        for detail in data.get("details", []):
            reason = detail.get("reason", "")
            if reason in ("API_KEY_INVALID","API_KEY_EXPIRED","API_KEY_SERVICE_BLOCKED","API_KEY_HTTP_REFERRER_BLOCKED","API_KEY_IP_ADDRESS_BLOCKED","SERVICE_DISABLED","BILLING_DISABLED","CONSUMER_INVALID","RATE_LIMIT_EXCEEDED","API_KEY_NOT_FOUND","USER_PROJECT_DENIED"):
                reasons.add(reason)
        checks = {
            "invalid_key": ("api key not valid","api_key_invalid","api key is invalid","invalid api key","api key expired","api key was reported as leaked"),
            "billing": ("billing","paid tier","payment"),
            "location": ("location is not supported","region is not supported","country is not supported"),
            "model": ("model is not found","not supported for generatecontent","model not found","model is not supported"),
            "schema": ("responseschema","response_schema","response schema","responsejsonschema","json schema","schema validation","enum"),
            "thinking": ("thinking","thinkingbudget","thinkinglevel"),
            "permission": ("permission","restricted","not authorized","access denied"),
            "request": ("invalid json payload","unknown name","unknown field","invalid value"),
            "output_tokens": ("maxoutputtokens","max_output_tokens","output token"),
        }
        cats = [name for name, words in checks.items() if any(word in msg for word in words)]
        return "status=" + safe_status + " reasons=" + ",".join(sorted(reasons)) + " categories=" + ",".join(cats)
    except (ValueError, TypeError, AttributeError, OSError):
        return "unparseable provider error"

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
            print(f"FAIL fixture {i}: HTTP {exc.code} {diagnose_http(exc)}")
            if exc.code in (400, 401, 403, 404, 429):
                break
        except URLError:
            print(f"FAIL fixture {i}: network error")
        except (ValueError, KeyError, IndexError, TypeError, OSError):
            print(f"FAIL fixture {i}: invalid response or transport error")
    print(f"LIVE Gemini ({model}): {passed}/{len(fixtures)} correct routes")
    return 0 if passed == len(fixtures) else 1

if __name__ == "__main__":
    raise SystemExit(main())
