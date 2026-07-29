# 나의 대한민국 여행 기록

Python, Streamlit, Folium, SQLite로 만든 개인 여행 기록 웹앱입니다.

## 주요 기능

- 대한민국 17개 광역자치단체를 `가본 곳 / 가고 싶은 곳 / 미방문`으로 분류
- 지도 클릭으로 장소 위도와 경도 입력
- 음식점, 카페, 관광명소, 숙소 등 장소 마커 저장
- 방문일, 별점, 한줄평 기록
- 지역·카테고리·검색어 필터
- 기록 삭제
- CSV 백업

## 1. 로컬 설치

PowerShell에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

PowerShell 실행 정책 때문에 activate가 되지 않아도 위 명령은 작동합니다.

## 2. GitHub 구조

```text
korea_travel_log/
├─ streamlit_app.py
├─ requirements.txt
├─ README.md
└─ travel_log.db       # 최초 실행 시 자동 생성
```

개인 기록이 들어 있는 `travel_log.db`를 공개 저장소에 올리지 않는 것을 권장합니다.

`.gitignore` 예시:

```gitignore
.venv/
__pycache__/
travel_log.db
.streamlit/secrets.toml
```

## 3. Streamlit Community Cloud 배포

1. 위 파일을 GitHub 저장소에 업로드합니다.
2. Streamlit Community Cloud에서 새 앱을 생성합니다.
3. Repository: 본인의 저장소
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. Deploy를 누릅니다.

## 중요: 데이터 영구 저장

이 버전은 로컬 SQLite를 사용합니다.

- 개인 PC에서 실행: 기록이 계속 유지됩니다.
- Streamlit Community Cloud: 앱 재시작이나 재배포 시 DB 파일이 초기화될 수 있습니다.

실제 장기 운영은 Supabase(PostgreSQL) 연결을 권장합니다. 다음 버전에서
사용자 로그인, 사진 저장, Supabase DB를 붙일 수 있습니다.
