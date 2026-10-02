# RS Radar v14 검증 보고서

2026-10-01 수정본. 기존 v11 프로젝트에서 이어서 작업했습니다.

## 실제 확보 데이터

- FRED: 58개 시계열
- EIA: 8개 시계열
- 저장된 관측값: 335,000개
- 공식 일정 아카이브: 444개 이벤트. 미래 일정과 과거 일정이 함께 포함되며 실제 발표값 기록과는 다릅니다.
- NY Fed SOFR/EFFR: 실제 응답 확보, 개별 관측일과 수집 시각 표시
- 마지막 갱신 완료: 2026-10-01T09:52:57.093912+00:00
- 주식 가격: 0개. Yahoo 요청 제한으로 실패했습니다.
- 원자재 선물 및 시장 ETF/지수: 26개 등록 항목이 모두 unavailable 상태입니다.

## 이번 수정

- 데모 자동 fallback을 차단하고 누락 가격을 N/A로 표시했습니다.
- 선물·시장 히스토리도 검증 후 저장하며 다운로드 실패·시계열 축소 시 마지막 정상 데이터와 마지막 성공 시각을 보존합니다.
- 6개월 수익률, 200일 이동평균, 52주 고저 등은 필요한 관측값이 충분할 때만 계산합니다.
- 자산 간 비율은 같은 관측일끼리 계산합니다.
- 주식 빌드가 기존 독립 매크로 데이터 영역을 지우지 않도록 수정했습니다.
- extended 실행도 검증된 공식 일정 파서를 사용합니다.
- FRED 전체 히스토리 변환에서 기준일 조회를 한 번에 수행하도록 개선했습니다.
- 시계열 ID 중복, 불리언 가격, 데모 응답을 거부하는 검증을 추가했습니다.
- GitHub Pages 워크플로와 Windows 실행 파일을 포함했습니다.

## 검증 결과

| 검사 | 결과 |
|---|---|
| Python 테스트 | 31개 통과 |
| Python compileall | 통과 |
| JavaScript 구문 | app.js / terminal.js 통과 |
| HTML5 파싱 | parse5 오류 0개 |
| HTML ID / 참조 자산 검사 | 통과, 중복 ID 0개 |
| 발행 데이터 검사 | 66개 연결 시계열, 335,000개 관측값 통과 |
| DOM 테스트 | 실제 스냅샷, 테스트 종목 조작, HTTP 503, 데모 차단 4개 시나리오 통과 |
| 메뉴 탐색 | 각 시나리오에서 49개 탭 탐색, 단일 활성 화면 검사 통과 |
| 실제 FRED / EIA 요청 | HTTP 200 확인 |
| Yahoo 수집 | HTTP 429 / YFRateLimitError로 실패 |
| 실제 Desktop/Mobile 시각 검사 | 미완료. 클라우드 브라우저가 로컬 미리보기 주소를 차단했고 로컬 브라우저 실행 파일이 없었습니다. |
| GitHub Actions / Pages 실제 실행 | 미완료. 연결된 접근 가능 저장소가 조회되지 않았습니다. |

DOM 테스트용 예시 종목은 examples 폴더에만 있으며 발행 web 폴더의 실제 데이터로 사용하지 않습니다.
테스트 통과는 실제 주식 데이터 연결·종목 분석 완성을 의미하지 않습니다.

## 남은 작업

1. 배포할 GitHub 저장소 연결 후 Actions와 Pages 실제 실행.
2. Yahoo 제한 해소 또는 사용 허가가 확인된 가격 공급자 연결 후 전 종목·선물 검증.
3. SEC_USER_AGENT 설정 후 SEC 재무·Form 4·13F 데이터 검증.
4. OPEC / Treasury / ISM / 신규실업수당 일정, 발표 actual / forecast / surprise 연결.
5. 실제 브라우저의 Desktop/Mobile 레이아웃 및 종목 데이터가 있는 포트폴리오·백테스트 검증.

## 참고한 공식 문서

- GitHub Pages 워크플로: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- FRED 데이터 다운로드: https://fredhelp.stlouisfed.org/fred/data/downloading/using-the-download-data-link/

추가 유료 API 호출과 OpenAI API 호출은 이번 갱신에서 수행하지 않았습니다.
