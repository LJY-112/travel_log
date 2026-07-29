# 나의 대한민국 여행 기록 v2

Python, Streamlit, Folium, OpenStreetMap, SQLite로 만든 개인 여행 기록 웹앱입니다.

## v2 변경 사항

- 기본 지도를 OpenStreetMap 표준 지도로 변경
- 지도 높이 확대 및 전체 화면 버튼 추가
- 17개 광역자치단체 아래에 시·군·구 229개 여행 분류 항목 추가
- 시·군·구별 `가본 곳 / 가고 싶은 곳 / 미방문` 상태 관리
- 지도와 장소 목록을 광역자치단체 및 시·군·구로 필터링
- 기존 장소 기록의 장소명, 지역, 카테고리, 방문일, 평점, 한줄평, 좌표 수정
- 구버전 SQLite 데이터베이스 자동 호환

## 로컬 실행

PowerShell에서 프로젝트 폴더로 이동합니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

PowerShell 실행 정책 때문에 가상환경 활성화가 되지 않아도 위 방식으로 실행할 수 있습니다.

## 기존 버전에서 업데이트

기존 폴더의 `streamlit_app.py`를 새 파일로 교체하고 앱을 다시 실행하면 됩니다.

기존 `travel_log.db`를 그대로 두면 장소 기록은 유지됩니다. 최초 실행 시 다음 작업이 자동으로 수행됩니다.

- `area_status` 테이블 생성
- 장소 기록에 `updated_at` 열 추가
- 기존 도시명이 새 시·군·구 이름과 일치하는 경우 해당 지역을 `가본 곳`으로 전환

중요한 데이터는 업데이트 전에 `travel_log.db`를 별도로 복사해 두는 것을 권장합니다.

## Streamlit Community Cloud

- Repository: GitHub 저장소
- Branch: `main`
- Main file path: `streamlit_app.py`

하위 폴더에 저장했다면 예시는 다음과 같습니다.

```text
korea_travel_log/streamlit_app.py
```

## 데이터 영구 저장 주의

로컬 PC에서는 `travel_log.db`가 유지됩니다. Streamlit Community Cloud의 로컬 파일은 재배포나 앱 재시작 때 초기화될 수 있으므로 장기 운영에는 Supabase 같은 외부 데이터베이스가 적합합니다.
