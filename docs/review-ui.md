# 담당자 검토 UI — 핵심 기능 02

기준: feature/double-check-engine (f603ec6). 기존 시민 화면, Supabase 테이블 및 AI 엔진 API를 유지한다.

## 변경 사항
- 결재선 부서·순번에 따라 접수/심사/승인 화면과 오류 상세 및 증빙 표시 범위를 분리.
- 현재 단계만 처리, 이전 단계는 상태만 표시, 이후 단계는 숨김.
- 오탈자 참조값 대조, 단계별 담당자 확인 후 전달, 기존 상태 조건으로 갱신.
- 증빙 파일명 또는 시연용 문서 유형 기준의 열람 범위와 wf_view_log 연동.

## 실행 및 테스트
기존 README의 Supabase 및 AI 엔진 설정을 따른다. 별도 마이그레이션 없음.
node tests/review-workflow.test.js — 권한/단계 판정 테스트 19개 통과. 브라우저·원격 DB·AI 엔진 통합 테스트는 미진행.

## 제한
합성 데이터 전용 UI 시연이다. 기존 RLS 공개 접근 정책 때문에 실제 인증이나 서버측 접근 제어를 제공하지 않는다. 개인정보 입력 금지. 문서 종류 매핑은 시연용이고 재검증은 참조값 대조이며 전체 AI 재실행이 아니다. 실제 결재·급여 결정은 수행하지 않는다.

상세 기획 및 작업 기록: https://app.notion.com/p/41d9ffcd2d168178bdc3c52e8e7a8963

## 추가 통합 검증 (모의 API)
`node tests/review-integration.test.js` — 15개 통과. 실제 index.html의 JS와 권한 모듈을 모의 DOM 및 Supabase/AI 응답으로 실행했다. 실제 브라우저, 운영 DB, 실제 AI 판독은 아직 미검증이다. 실 DB 변경 없음.

## 실제 API 연결 점검
`python3 tests/live_api_smoke.py`로 Supabase 읽기 4종과 로컬 AI health 확인. 합성 PDF/TXT 및 해당 절차·서류 ID를 `--fixture`, `--proc-id`, `--doc-id`로 지정하면 엔진 POST 2종도 확인한다. 공유 DB 쓰기는 하지 않는다. 현재 실행 환경에서 DNS 해석 실패, 로컬 엔진 연결 거부로 실제 API 결과 미검증.

## 시민 신청 도우미 챗봇 개선
- DB 장애에도 챗봇 초기화, seed.sql의 합성 서비스·서류 정의로 안내하는 읽기 전용 fallback.
- 서비스 선택/질문 내 서비스 인식, 서류·준비 방법·자격·대리 신청·상태 안내. DB 상태 조회 실패 시 추측하지 않음.
- 문자/메일은 동의 확인 후 미리보기만 제공, 실제 발송 및 DB 기록 없음. 별도 LLM/AI 엔진 불필요.
- `node tests/chatbot.test.js`: 19건 통과 (모의 DOM·API). 기존 단위 19건, 통합 15건 재검증 통과. 실제 브라우저 및 외부 API 미검증.

## 실제 엔진 연결 점검 결과 (2026-11-20, 권승빈)
`python3 tests/live_api_smoke.py --fixture 이직확인서_홍길동_합성.pdf --proc-id s1 --doc-id s1d3` (엔진 규칙 판독 모드)
- PASS: wf_procedures · wf_proc_docs · wf_approval_line 읽기, engine health, check-doc(state=ok), check-case(findings=4)
- FAIL 1건: wf_cases 조회 HTTP 400 — 공유 DB에 `findings` 칸이 아직 없음 (`migrations/002_double_check.sql` 미적용, 의도적으로 보류 중)
- 병합 후 `node tests/*.test.js` 53건(19+15+19) 모두 통과

## LLM 질문 분류 (별도 브랜치)
- 기존 Gemini 판독 엔진과 독립적인 127.0.0.1 로컬 챗봇 서버. 사용자가 명시적으로 AI 질문 분류 켜기 선택 시 일반 질문과 서비스 ID만 전송.
- 분류 결과의 허용 의도·서비스 ID 검증 후 기존 DB/seed 기반 안내. 모델의 자유 텍스트를 안내로 표시하지 않음. 상태·발송·기간 질문은 로컬 처리. 오류 시 규칙 기반 fallback.
- 모델 키는 환경변수, 실제 외부 Gemini API 응답은 키/모델이 제공되지 않아 아직 미검증. 운영 인증 및 실제 개인정보 사용 범위 아님.
- Chromium 기존 챗봇 검증 PASS: https://github.com/who0oami/OnePiece_SAKAK/actions/runs/44672181476 (외부 DB/판독 엔진 차단).

## 실제 LLM 검증 준비
- 기본 모델: `gemini-3.5-flash-lite` (계정별 모델 접근 여부는 실제 호출로 검증 필요). 환경변수로 변경 가능.
- `tests/live_gemini_smoke.py`: 합성 질문 3개를 실제 Gemini REST API로 분류해 expected intent + pid 일치 여부 확인. 키 없는 경우 미실행으로 기록.
- CI에서 `GEMINI_API_KEY` secret이 존재할 때만 호출. 모델 접근/실제 응답 품질은 테스트 로그가 통과해야 확인된 것으로 간주한다.
