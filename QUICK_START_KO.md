# RS Radar v14 실행과 배포

## Windows에서 열기

ZIP을 압축 해제하고 `START_WINDOWS.cmd`를 실행하세요. Python 3가 설치돼 있어야 합니다.
브라우저가 열리지 않으면 `http://127.0.0.1:8000`에 접속하세요.
`web/index.html`을 파일 탐색기에서 직접 열면 브라우저의 JSON 읽기 제한 때문에 데이터를 불러오지 못할 수 있습니다.
화면을 보는 데는 API 키나 추가 Python 패키지가 필요하지 않습니다.

## 직접 데이터 갱신

프로젝트 폴더에서 다음을 실행하세요.

```bash
python -m pip install -r requirements-dev.txt
python -m scripts.refresh --extended
```

Yahoo가 요청을 제한하면 주식·선물 가격은 N/A로 남습니다. 이미 검증된 과거 데이터가 있으면 마지막 정상 데이터를 유지하고 stale로 표시합니다.
매크로만 갱신하려면 `python -m scripts.refresh --macro-only`를 사용하세요.

## GitHub Pages

프로젝트 파일을 배포할 저장소의 main 브랜치에 올리세요. 저장소 Settings → Pages → Source를 GitHub Actions로 선택하고,
Actions의 **Refresh verified data and deploy Pages**를 실행하세요.
워크플로는 데이터 수집·계산·검증 후 web 폴더를 배포하며, 미국 영업일의 22:30 UTC에 갱신합니다.
한국 시간으로 다음 날 07:30이며, GitHub 예약 실행은 지연될 수 있습니다.

FRED CSV, NY Fed, EIA, 공식 일정은 키 없이 연결됩니다. SEC를 사용하려면 저장소 Secret `SEC_USER_AGENT`에
조직 이름과 연락 이메일을 입력하세요. `OPENAI_API_KEY`는 별도 공시 요약 기능에만 쓰는 선택값이며 기본 갱신에서 사용하지 않습니다.

실제 GitHub 저장소 업로드·Actions 실행·Pages 배포는 이번 작업에서 완료되지 않았습니다.
현재 연결에서 접근 가능한 저장소가 조회되지 않았습니다.

## 현재 데이터 범위

FRED 58개, EIA 8개 시계열과 공식 경제 일정이 포함돼 있습니다. 주식·선물·시장 ETF 가격은 이번 수집에서
Yahoo의 요청 제한으로 확보하지 못했습니다. SEC·추정실적·소유구조·종목 백테스트는 실제 종목 입력이 확보된 뒤 검증해야 합니다.
OPEC, 국채 입찰, ISM, 신규실업수당 일정과 발표 actual/forecast/surprise는 아직 연결되지 않았습니다.
Desktop/Mobile CSS를 제공하지만 실제 브라우저 시각 검증은 완료하지 못했습니다.
