# 나의 대한민국 여행 기록 v4

OpenStreetMap + Streamlit + Supabase PostgreSQL/Storage 기반 개인 여행 기록 앱입니다.

## v4 추가 기능

- 장소를 새로 저장할 때 사진을 함께 업로드
- 기존 장소에 사진 추가
- 장소별 3열 사진 갤러리
- 사진 설명 수정
- 대표사진 지정
- 개별 사진 삭제
- 장소 삭제 시 Storage의 연결 사진도 함께 삭제
- 비공개 Supabase Storage bucket과 1시간짜리 signed URL 사용

## 업데이트 순서

1. Supabase Dashboard의 **SQL Editor**에서 최신 `supabase_schema.sql` 전체를 다시 실행합니다.
   - 기존 `places`, `area_status` 데이터는 삭제되지 않습니다.
   - `place_photos` 테이블과 `travel-photos` Storage bucket이 추가됩니다.
2. 기존 프로젝트의 `streamlit_app.py`, `supabase_schema.sql`, `README.md`를 v4 파일로 교체합니다.
3. 패키지를 확인하고 앱을 다시 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## 사진 사용법

### 새 장소와 함께 업로드

`여행 지도 → 새 장소 기록`에서 장소 정보와 사진을 선택합니다.
한 번에 최대 8장, 각 파일은 10MB 이하이며 JPG/JPEG/PNG/WEBP를 지원합니다.
첫 번째 사진은 자동으로 대표사진이 됩니다.

### 기존 장소에 추가

`사진 갤러리` 탭에서 장소를 선택하고 사진을 업로드합니다.
사진 아래의 `사진 정보 수정·삭제`에서 설명, 대표사진, 삭제를 관리합니다.

## Storage 보안

`travel-photos` bucket은 비공개입니다. 앱은 Supabase Secret key를 서버에서만 사용하고,
화면 표시 시 1시간 동안 유효한 signed URL을 생성합니다. Secret key와
`.streamlit/secrets.toml`은 GitHub에 올리지 마세요.

## Secrets

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
secret_key = "sb_secret_YOUR_SECRET_KEY"

[app]
password = "나만의-접속-비밀번호"
```
