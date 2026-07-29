# 나의 대한민국 여행 기록 v3

OpenStreetMap + Streamlit + Supabase PostgreSQL 기반 개인 여행 기록 웹앱입니다.

## v3 핵심 변경

- SQLite 대신 Supabase PostgreSQL에 장소와 방문 상태 영구 저장
- Streamlit Secrets를 통한 Supabase URL 및 Secret key 관리
- 간단한 앱 비밀번호 로그인
- 기존 `travel_log.db` 데이터를 Supabase로 중복 없이 이전
- CSV 백업 유지

## 1. Supabase 프로젝트 생성

1. Supabase에서 새 프로젝트를 만듭니다.
2. 프로젝트 Dashboard의 **SQL Editor**를 엽니다.
3. 이 프로젝트에 포함된 `supabase_schema.sql` 전체를 붙여넣고 실행합니다.
4. **Project Settings → API Keys**에서 다음 값을 확인합니다.
   - Project URL
   - Secret key (`sb_secret_...`)

Secret key는 서버 전용입니다. GitHub, 채팅, 화면 캡처, 클라이언트 JavaScript에 공개하면 안 됩니다.

## 2. 로컬 Secrets 설정

프로젝트 폴더에 `.streamlit/secrets.toml`을 만듭니다.

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
secret_key = "sb_secret_YOUR_SECRET_KEY"

[app]
password = "나만의-접속-비밀번호"
```

`secrets.toml`은 `.gitignore`에 포함되어 있으므로 GitHub에 업로드하지 않습니다.

## 3. 로컬 실행

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## 4. 기존 SQLite 기록 이전

기존 `travel_log.db`를 `streamlit_app.py`와 같은 폴더에 둡니다.
앱 로그인 후 **백업 → 기존 SQLite 데이터 가져오기**에서 이전 버튼을 누릅니다.

- `area_status` 방문 상태를 upsert
- `places` 장소 기록을 이전
- 기존 SQLite ID를 `legacy_sqlite_id`로 저장
- 같은 이전 작업을 다시 실행해도 장소가 중복되지 않음

이전 완료 후에도 안전을 위해 원본 `travel_log.db`를 별도로 보관하세요.

## 5. Streamlit Community Cloud 배포

GitHub에는 다음 파일을 올립니다.

```text
streamlit_app.py
requirements.txt
supabase_schema.sql
README.md
.gitignore
```

Community Cloud 앱 설정에서:

```text
Repository: 본인의 GitHub 저장소
Branch: main
Main file path: streamlit_app.py
```

**App settings → Secrets**에 로컬 `secrets.toml`과 같은 내용을 입력합니다.

## 보안 구조

- Supabase 테이블에는 RLS가 활성화됩니다.
- `anon` 및 `authenticated` 역할에는 테이블 권한을 부여하지 않습니다.
- Streamlit 서버만 Secret key로 DB에 접근합니다.
- 앱 자체에는 별도의 접속 비밀번호가 적용됩니다.

이 구조는 개인용 단일 사용자 앱에 적합합니다. 여러 사용자가 각자 계정을 갖는 서비스로 확장할 때는 Supabase Auth와 `user_id` 기반 RLS 정책으로 변경해야 합니다.
