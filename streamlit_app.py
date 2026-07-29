from __future__ import annotations

import hashlib
import hmac
import html
import sqlite3
import mimetypes
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Fullscreen, MarkerCluster
from streamlit_folium import st_folium
from supabase import Client, create_client

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "travel_log.db"
PHOTO_BUCKET = "travel-photos"
MAX_PHOTOS_PER_UPLOAD = 8
MAX_PHOTO_BYTES = 10 * 1024 * 1024

PROVINCE_CENTERS = {
    "서울특별시": (37.5665, 126.9780),
    "부산광역시": (35.1796, 129.0756),
    "대구광역시": (35.8714, 128.6014),
    "인천광역시": (37.4563, 126.7052),
    "광주광역시": (35.1595, 126.8526),
    "대전광역시": (36.3504, 127.3845),
    "울산광역시": (35.5384, 129.3114),
    "세종특별자치시": (36.4800, 127.2890),
    "경기도": (37.4138, 127.5183),
    "강원특별자치도": (37.8228, 128.1555),
    "충청북도": (36.6357, 127.4917),
    "충청남도": (36.6588, 126.6728),
    "전북특별자치도": (35.7175, 127.1530),
    "전라남도": (34.8679, 126.9910),
    "경상북도": (36.4919, 128.8889),
    "경상남도": (35.4606, 128.2132),
    "제주특별자치도": (33.4996, 126.5312),
}

# 여행 기록에 적합하도록 광역자치단체 아래의 시·군·구를 2단계로 구성합니다.
ADMIN_AREAS = {
    "서울특별시": [
        "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
        "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구",
        "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구",
        "서초구", "강남구", "송파구", "강동구",
    ],
    "부산광역시": [
        "중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구",
        "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군",
    ],
    "대구광역시": [
        "중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군",
    ],
    "인천광역시": [
        "중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구",
        "강화군", "옹진군",
    ],
    "광주광역시": ["동구", "서구", "남구", "북구", "광산구"],
    "대전광역시": ["동구", "중구", "서구", "유성구", "대덕구"],
    "울산광역시": ["중구", "남구", "동구", "북구", "울주군"],
    "세종특별자치시": ["세종시 전역"],
    "경기도": [
        "수원시", "용인시", "고양시", "화성시", "성남시", "부천시", "남양주시",
        "안산시", "평택시", "안양시", "시흥시", "파주시", "김포시", "의정부시",
        "광주시", "하남시", "광명시", "군포시", "양주시", "오산시", "이천시",
        "안성시", "구리시", "의왕시", "포천시", "양평군", "여주시", "동두천시",
        "과천시", "가평군", "연천군",
    ],
    "강원특별자치도": [
        "춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군",
        "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군",
        "고성군", "양양군",
    ],
    "충청북도": [
        "청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군",
        "괴산군", "음성군", "단양군",
    ],
    "충청남도": [
        "천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시",
        "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군",
    ],
    "전북특별자치도": [
        "전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군",
        "무주군", "장수군", "임실군", "순창군", "고창군", "부안군",
    ],
    "전라남도": [
        "목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군",
        "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군",
        "함평군", "영광군", "장성군", "완도군", "진도군", "신안군",
    ],
    "경상북도": [
        "포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시",
        "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군",
        "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군",
    ],
    "경상남도": [
        "창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시",
        "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군",
        "거창군", "합천군",
    ],
    "제주특별자치도": ["제주시", "서귀포시"],
}

STATUS_OPTIONS = ["가본 곳", "가고 싶은 곳", "미방문"]
CATEGORY_OPTIONS = ["음식점", "카페", "관광명소", "숙소", "쇼핑", "자연", "기타"]

STATUS_COLORS = {
    "가본 곳": "#198754",
    "가고 싶은 곳": "#F59E0B",
    "미방문": "#94A3B8",
}

CATEGORY_ICONS = {
    "음식점": "cutlery",
    "카페": "coffee",
    "관광명소": "camera",
    "숙소": "bed",
    "쇼핑": "shopping-cart",
    "자연": "tree",
    "기타": "map-marker",
}

st.set_page_config(
    page_title="나의 대한민국 여행 기록",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Streamlit 상단 고정 헤더와 겹치지 않도록 충분한 안전 여백을 둡니다. */
    .block-container {
        padding-top: 4.75rem !important;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    /* 한글 상단 획과 이모지가 잘리지 않도록 line-height와 내부 여백을 명시합니다. */
    .travel-title {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        min-height: 3.4rem;
        margin: 0 0 0.15rem 0;
        padding: 0.25rem 0 0.15rem 0;
        overflow: visible;
        font-size: 2.15rem;
        font-weight: 800;
        line-height: 1.35;
        letter-spacing: -0.025em;
    }

    .travel-title-icon {
        display: inline-flex;
        align-items: center;
        line-height: 1;
        flex: 0 0 auto;
    }

    .travel-title-text {
        display: inline-block;
        line-height: 1.35;
        overflow: visible;
    }

    .travel-sub {
        color: #64748b;
        margin: 0 0 1rem 0;
        line-height: 1.6;
    }

    div[data-testid="stForm"] {border-radius: 14px;}
    iframe {border-radius: 14px;}

    @media (max-width: 768px) {
        .block-container {padding-top: 4.35rem !important;}
        .travel-title {font-size: 1.75rem; min-height: 3rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_app_config() -> tuple[str, str, str]:
    """Streamlit Secrets에서 Supabase와 앱 비밀번호 설정을 읽습니다."""
    try:
        supabase_config = st.secrets["supabase"]
        app_config = st.secrets["app"]
        url = str(supabase_config["url"]).strip()
        secret_key = str(supabase_config["secret_key"]).strip()
        app_password = str(app_config["password"])
    except (FileNotFoundError, KeyError) as exc:
        st.error("Supabase 연결 정보가 설정되지 않았습니다.")
        st.code(
            '[supabase]\n'
            'url = "https://YOUR_PROJECT_REF.supabase.co"\n'
            'secret_key = "sb_secret_YOUR_SECRET_KEY"\n\n'
            '[app]\n'
            'password = "나만의-접속-비밀번호"',
            language="toml",
        )
        st.info(
            "로컬에서는 프로젝트 폴더의 `.streamlit/secrets.toml`에 저장하고, "
            "Streamlit Community Cloud에서는 App settings → Secrets에 같은 내용을 입력하세요."
        )
        st.stop()
        raise RuntimeError("unreachable") from exc

    if not url.startswith("https://") or not secret_key or not app_password:
        st.error("Secrets의 Supabase URL, secret_key, 앱 비밀번호를 확인해 주세요.")
        st.stop()
    return url, secret_key, app_password


@st.cache_resource(show_spinner=False)
def get_supabase_client(url: str, secret_key: str) -> Client:
    return create_client(url, secret_key)


def require_app_password(expected_password: str) -> None:
    """공개 Streamlit 주소에서 다른 사람이 기록을 수정하지 못하도록 보호합니다."""
    expected_hash = hashlib.sha256(expected_password.encode("utf-8")).hexdigest()
    if st.session_state.get("travel_auth_hash") == expected_hash:
        return

    st.markdown(
        """
        <div class="travel-title">
            <span class="travel-title-icon">🔐</span>
            <span class="travel-title-text">여행 기록 로그인</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="travel-sub">Supabase에 저장된 개인 여행 기록을 열려면 비밀번호를 입력하세요.</div>',
        unsafe_allow_html=True,
    )
    with st.form("travel_password_form"):
        entered = st.text_input("접속 비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)
        if submitted:
            if hmac.compare_digest(entered, expected_password):
                st.session_state["travel_auth_hash"] = expected_hash
                st.rerun()
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()


def verify_supabase_schema(client: Client) -> None:
    """필수 테이블 존재 여부와 접속 권한을 확인합니다."""
    try:
        client.table("area_status").select("province", count="exact").limit(1).execute()
        client.table("places").select("id", count="exact").limit(1).execute()
        client.table("place_photos").select("id", count="exact").limit(1).execute()
    except Exception as exc:
        st.error("Supabase에는 연결했지만 필요한 테이블을 확인할 수 없습니다.")
        st.info("프로젝트에 포함된 `supabase_schema.sql`을 Supabase SQL Editor에서 먼저 실행하세요.")
        with st.expander("오류 세부 정보"):
            st.code(str(exc))
        st.stop()


def ensure_area_reference_rows(client: Client) -> None:
    """새 프로젝트의 area_status에 229개 시·군·구 기준 행을 한 번 채웁니다."""
    try:
        response = client.table("area_status").select("province,subregion").execute()
        existing = {
            (str(row["province"]), str(row["subregion"]))
            for row in (response.data or [])
        }
        now = now_utc_iso()
        missing = [
            {
                "province": province,
                "subregion": subregion,
                "status": "미방문",
                "updated_at": now,
            }
            for province, subregions in ADMIN_AREAS.items()
            for subregion in subregions
            if (province, subregion) not in existing
        ]
        if missing:
            client.table("area_status").insert(missing).execute()
    except Exception as exc:
        st.error("시·군·구 초기 데이터를 Supabase에 생성하지 못했습니다.")
        with st.expander("오류 세부 정보"):
            st.code(str(exc))
        st.stop()


def load_area_status(province: Optional[str] = None) -> pd.DataFrame:
    client = st.session_state["supabase_client"]
    query = client.table("area_status").select("province,subregion,status,updated_at")
    if province:
        query = query.eq("province", province)
    response = query.order("province").order("subregion").execute()
    columns = ["province", "subregion", "status", "updated_at"]
    return pd.DataFrame(response.data or [], columns=columns)


def update_area_status(province: str, subregion: str, status: str) -> None:
    client = st.session_state["supabase_client"]
    client.table("area_status").upsert(
        {
            "province": province,
            "subregion": subregion,
            "status": status,
            "updated_at": now_utc_iso(),
        },
        on_conflict="province,subregion",
    ).execute()


def update_area_statuses(rows: pd.DataFrame) -> None:
    client = st.session_state["supabase_client"]
    now = now_utc_iso()
    payload = [
        {
            "province": str(row.province),
            "subregion": str(row.subregion),
            "status": str(row.status),
            "updated_at": now,
        }
        for row in rows.itertuples(index=False)
    ]
    if payload:
        client.table("area_status").upsert(
            payload,
            on_conflict="province,subregion",
        ).execute()


def load_places() -> pd.DataFrame:
    client = st.session_state["supabase_client"]
    columns = [
        "id", "legacy_sqlite_id", "region", "city", "place_name", "category",
        "visit_date", "rating", "one_line_review", "latitude", "longitude",
        "created_at", "updated_at",
    ]
    rows: list[dict[str, Any]] = []
    page_size = 1000
    start = 0
    while True:
        response = (
            client.table("places")
            .select(",".join(columns))
            .order("visit_date", desc=True, nullsfirst=False)
            .order("id", desc=True)
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return pd.DataFrame(rows, columns=columns)


def add_place(
    region: str,
    city: str,
    place_name: str,
    category: str,
    visit_date: Optional[str],
    rating: int,
    review: str,
    latitude: float,
    longitude: float,
) -> int:
    client = st.session_state["supabase_client"]
    now = now_utc_iso()
    response = client.table("places").insert(
        {
            "region": region,
            "city": city,
            "place_name": place_name.strip(),
            "category": category,
            "visit_date": visit_date,
            "rating": int(rating),
            "one_line_review": review.strip(),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "created_at": now,
            "updated_at": now,
        }
    ).execute()
    update_area_status(region, city, "가본 곳")
    rows = response.data or []
    if not rows:
        raise RuntimeError("저장된 장소 ID를 확인하지 못했습니다.")
    return int(rows[0]["id"])


def update_place(
    place_id: int,
    region: str,
    city: str,
    place_name: str,
    category: str,
    visit_date: Optional[str],
    rating: int,
    review: str,
    latitude: float,
    longitude: float,
) -> None:
    client = st.session_state["supabase_client"]
    (
        client.table("places")
        .update(
            {
                "region": region,
                "city": city,
                "place_name": place_name.strip(),
                "category": category,
                "visit_date": visit_date,
                "rating": int(rating),
                "one_line_review": review.strip(),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "updated_at": now_utc_iso(),
            }
        )
        .eq("id", int(place_id))
        .execute()
    )
    update_area_status(region, city, "가본 곳")


def delete_place(place_id: int) -> None:
    client = st.session_state["supabase_client"]
    delete_all_place_photos(int(place_id))
    client.table("places").delete().eq("id", int(place_id)).execute()



def sanitize_filename(filename: str) -> str:
    """Storage 경로에 안전한 파일명 일부를 만듭니다."""
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    clean = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", stem).strip("-_")
    return f"{clean[:50] or 'photo'}{suffix}"


def load_place_photos(place_id: Optional[int] = None) -> pd.DataFrame:
    client = st.session_state["supabase_client"]
    columns = [
        "id", "place_id", "storage_path", "original_name", "caption",
        "is_cover", "sort_order", "created_at",
    ]
    query = client.table("place_photos").select(",".join(columns))
    if place_id is not None:
        query = query.eq("place_id", int(place_id))
    response = query.order("is_cover", desc=True).order("sort_order").order("id").execute()
    return pd.DataFrame(response.data or [], columns=columns)


def signed_photo_url(storage_path: str, expires_in: int = 3600) -> str:
    client = st.session_state["supabase_client"]
    response = client.storage.from_(PHOTO_BUCKET).create_signed_url(storage_path, expires_in)
    if isinstance(response, dict):
        return str(response.get("signedURL") or response.get("signed_url") or "")
    return str(getattr(response, "signed_url", "") or getattr(response, "signedURL", ""))


def upload_place_photos(place_id: int, uploaded_files: list[Any]) -> int:
    """여러 이미지를 Storage에 저장하고 메타데이터 행을 생성합니다."""
    if not uploaded_files:
        return 0
    if len(uploaded_files) > MAX_PHOTOS_PER_UPLOAD:
        raise ValueError(f"한 번에 최대 {MAX_PHOTOS_PER_UPLOAD}장까지 업로드할 수 있습니다.")

    client = st.session_state["supabase_client"]
    existing = load_place_photos(place_id)
    existing_count = len(existing)
    uploaded_paths: list[str] = []
    metadata: list[dict[str, Any]] = []

    try:
        for index, uploaded in enumerate(uploaded_files):
            raw = uploaded.getvalue()
            if len(raw) > MAX_PHOTO_BYTES:
                raise ValueError(f"{uploaded.name}: 파일 크기가 10MB를 초과합니다.")
            content_type = str(getattr(uploaded, "type", "") or mimetypes.guess_type(uploaded.name)[0] or "")
            if not content_type.startswith("image/"):
                raise ValueError(f"{uploaded.name}: 이미지 파일만 업로드할 수 있습니다.")

            safe_name = sanitize_filename(uploaded.name)
            storage_path = f"places/{int(place_id)}/{uuid.uuid4().hex}_{safe_name}"
            client.storage.from_(PHOTO_BUCKET).upload(
                path=storage_path,
                file=raw,
                file_options={"content-type": content_type, "upsert": "false"},
            )
            uploaded_paths.append(storage_path)
            metadata.append(
                {
                    "place_id": int(place_id),
                    "storage_path": storage_path,
                    "original_name": str(uploaded.name),
                    "caption": "",
                    "is_cover": existing_count == 0 and index == 0,
                    "sort_order": existing_count + index,
                    "created_at": now_utc_iso(),
                }
            )
        if metadata:
            client.table("place_photos").insert(metadata).execute()
        return len(metadata)
    except Exception:
        if uploaded_paths:
            try:
                client.storage.from_(PHOTO_BUCKET).remove(uploaded_paths)
            except Exception:
                pass
        raise


def update_photo_metadata(photo_id: int, caption: str, is_cover: bool, place_id: int) -> None:
    client = st.session_state["supabase_client"]
    if is_cover:
        client.table("place_photos").update({"is_cover": False}).eq("place_id", int(place_id)).execute()
    client.table("place_photos").update(
        {"caption": caption.strip(), "is_cover": bool(is_cover)}
    ).eq("id", int(photo_id)).execute()


def delete_photo(photo_id: int) -> None:
    client = st.session_state["supabase_client"]
    response = client.table("place_photos").select("storage_path").eq("id", int(photo_id)).limit(1).execute()
    rows = response.data or []
    if not rows:
        return
    storage_path = str(rows[0]["storage_path"])
    client.storage.from_(PHOTO_BUCKET).remove([storage_path])
    client.table("place_photos").delete().eq("id", int(photo_id)).execute()


def delete_all_place_photos(place_id: int) -> None:
    photos = load_place_photos(place_id)
    if photos.empty:
        return
    client = st.session_state["supabase_client"]
    paths = photos["storage_path"].astype(str).tolist()
    if paths:
        client.storage.from_(PHOTO_BUCKET).remove(paths)
    client.table("place_photos").delete().eq("place_id", int(place_id)).execute()


def sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def sqlite_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate_sqlite_to_supabase() -> tuple[int, int]:
    """기존 travel_log.db를 반복 실행해도 중복 없이 Supabase로 옮깁니다."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite 파일을 찾을 수 없습니다: {DB_PATH}")

    client = st.session_state["supabase_client"]
    imported_area_count = 0
    imported_place_count = 0

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        if sqlite_table_exists(conn, "area_status"):
            area_rows = conn.execute(
                "SELECT province, subregion, status, updated_at FROM area_status"
            ).fetchall()
            area_payload = [
                {
                    "province": str(row["province"]),
                    "subregion": str(row["subregion"]),
                    "status": str(row["status"]),
                    "updated_at": str(row["updated_at"] or now_utc_iso()),
                }
                for row in area_rows
                if str(row["province"]) in ADMIN_AREAS
                and str(row["subregion"]) in ADMIN_AREAS[str(row["province"])]
            ]
            if area_payload:
                client.table("area_status").upsert(
                    area_payload,
                    on_conflict="province,subregion",
                ).execute()
                imported_area_count = len(area_payload)

        if sqlite_table_exists(conn, "places"):
            cols = sqlite_columns(conn, "places")
            select_columns = [
                "id", "region", "city", "place_name", "category", "visit_date",
                "rating", "one_line_review", "latitude", "longitude", "created_at",
            ]
            if "updated_at" in cols:
                select_columns.append("updated_at")
            place_rows = conn.execute(
                f"SELECT {','.join(select_columns)} FROM places ORDER BY id"
            ).fetchall()

            payload: list[dict[str, Any]] = []
            visited_pairs: set[tuple[str, str]] = set()
            for row in place_rows:
                province = str(row["region"])
                raw_city = str(row["city"])
                city = canonical_subregion(province, raw_city) or raw_city
                created_at = str(row["created_at"] or now_utc_iso())
                updated_at = (
                    str(row["updated_at"] or created_at)
                    if "updated_at" in cols
                    else created_at
                )
                payload.append(
                    {
                        "legacy_sqlite_id": int(row["id"]),
                        "region": province,
                        "city": city,
                        "place_name": str(row["place_name"]),
                        "category": str(row["category"]),
                        "visit_date": row["visit_date"],
                        "rating": int(row["rating"]),
                        "one_line_review": str(row["one_line_review"]),
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }
                )
                if province in ADMIN_AREAS and city in ADMIN_AREAS[province]:
                    visited_pairs.add((province, city))

            for start in range(0, len(payload), 200):
                client.table("places").upsert(
                    payload[start:start + 200],
                    on_conflict="legacy_sqlite_id",
                ).execute()
            imported_place_count = len(payload)

            if visited_pairs:
                now = now_utc_iso()
                client.table("area_status").upsert(
                    [
                        {
                            "province": province,
                            "subregion": city,
                            "status": "가본 곳",
                            "updated_at": now,
                        }
                        for province, city in sorted(visited_pairs)
                    ],
                    on_conflict="province,subregion",
                ).execute()

    return imported_area_count, imported_place_count


def safe(value: object) -> str:
    return html.escape("" if value is None else str(value))


def province_summary(area_df: pd.DataFrame, province: str) -> tuple[int, int, int]:
    subset = area_df[area_df["province"] == province]
    visited = int((subset["status"] == "가본 곳").sum())
    wishlist = int((subset["status"] == "가고 싶은 곳").sum())
    return visited, wishlist, len(subset)


def build_map(
    area_df: pd.DataFrame,
    place_df: pd.DataFrame,
    selected_province: str,
    selected_subregion: str,
) -> folium.Map:
    filtered = place_df.copy()
    if selected_province != "전체" and not filtered.empty:
        filtered = filtered[filtered["region"] == selected_province]
    if selected_subregion != "전체" and not filtered.empty:
        filtered = filtered[filtered["city"] == selected_subregion]

    center = PROVINCE_CENTERS.get(selected_province, (36.35, 127.80))
    zoom = 9 if selected_province != "전체" else 7
    if len(filtered) == 1:
        center = (float(filtered.iloc[0]["latitude"]), float(filtered.iloc[0]["longitude"]))
        zoom = 14

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        min_zoom=6,
        max_zoom=19,
    )
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap 표준 지도",
        overlay=False,
        control=True,
        show=True,
        max_zoom=19,
    ).add_to(m)
    Fullscreen(position="topright", title="전체 화면", title_cancel="전체 화면 종료").add_to(m)

    provinces_to_show = (
        list(PROVINCE_CENTERS.keys())
        if selected_province == "전체"
        else [selected_province]
    )
    for province in provinces_to_show:
        lat, lon = PROVINCE_CENTERS[province]
        visited, wishlist, total = province_summary(area_df, province)
        if visited > 0:
            aggregate_status = "가본 곳"
        elif wishlist > 0:
            aggregate_status = "가고 싶은 곳"
        else:
            aggregate_status = "미방문"

        popup = (
            f"<b>{safe(province)}</b><br>"
            f"가본 곳: {visited}/{total}<br>"
            f"가고 싶은 곳: {wishlist}"
        )
        folium.CircleMarker(
            location=[lat, lon],
            radius=8 if selected_province == "전체" else 11,
            color="#ffffff",
            fill=True,
            fill_color=STATUS_COLORS[aggregate_status],
            fill_opacity=0.92,
            weight=2,
            tooltip=f"{province} · 방문 {visited}/{total}",
            popup=folium.Popup(popup, max_width=260),
        ).add_to(m)

    cluster = MarkerCluster(name="나의 장소 기록", show=True).add_to(m)
    for row in filtered.itertuples(index=False):
        visit_text = row.visit_date if pd.notna(row.visit_date) and row.visit_date else "날짜 미입력"
        stars = "★" * int(row.rating) + "☆" * (5 - int(row.rating))
        popup_html = f"""
        <div style="width:260px; line-height:1.55">
          <b style="font-size:15px">{safe(row.place_name)}</b><br>
          {safe(row.region)} · {safe(row.city)}<br>
          {safe(row.category)} · {safe(visit_text)}<br>
          <span style="color:#d97706">{stars}</span><br>
          <hr style="margin:7px 0">
          {safe(row.one_line_review)}<br>
          <small style="color:#64748b">기록 ID: {row.id}</small>
        </div>
        """
        folium.Marker(
            location=[row.latitude, row.longitude],
            tooltip=f"{row.place_name} · {row.category}",
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(
                color="blue",
                icon=CATEGORY_ICONS.get(row.category, "map-marker"),
                prefix="fa",
            ),
        ).add_to(cluster)

    if len(filtered) >= 2 and selected_subregion != "전체":
        bounds = [
            [float(filtered["latitude"].min()), float(filtered["longitude"].min())],
            [float(filtered["latitude"].max()), float(filtered["longitude"].max())],
        ]
        m.fit_bounds(bounds, padding=(35, 35), max_zoom=14)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def canonical_subregion(province: str, raw_city: str) -> Optional[str]:
    """기존 SQLite의 상세 주소를 현재 시·군·구 분류명으로 정규화합니다."""
    if province not in ADMIN_AREAS:
        return None
    city = str(raw_city).strip()
    if city in ADMIN_AREAS[province]:
        return city
    # 예: "전주시 완산구" -> "전주시", "서울특별시 강남구" -> "강남구"
    matches = [name for name in ADMIN_AREAS[province] if name in city]
    if not matches:
        return None
    return max(matches, key=len)


def parse_date(value: object) -> date:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return date.today()
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return date.today()


SUPABASE_URL, SUPABASE_SECRET_KEY, APP_PASSWORD = get_app_config()
require_app_password(APP_PASSWORD)
supabase_client = get_supabase_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
st.session_state["supabase_client"] = supabase_client
verify_supabase_schema(supabase_client)
if not st.session_state.get("supabase_area_seeded"):
    ensure_area_reference_rows(supabase_client)
    st.session_state["supabase_area_seeded"] = True

with st.sidebar:
    st.success("☁️ Supabase 연결됨")
    if st.button("로그아웃", use_container_width=True):
        st.session_state.pop("travel_auth_hash", None)
        st.rerun()

st.markdown(
    """
    <div class="travel-title">
        <span class="travel-title-icon">🧭</span>
        <span class="travel-title-text">나의 대한민국 여행 기록</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="travel-sub">OpenStreetMap에서 위치를 선택하고, 시·군·구별 방문 상태와 장소 기록을 관리합니다.</div>',
    unsafe_allow_html=True,
)

area_df = load_area_status()
place_df = load_places()

visited_count = int((area_df["status"] == "가본 곳").sum())
wishlist_count = int((area_df["status"] == "가고 싶은 곳").sum())
place_count = len(place_df)
area_place_count = int(place_df[["region", "city"]].drop_duplicates().shape[0]) if not place_df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("가본 시·군·구", f"{visited_count} / {len(area_df)}")
m2.metric("가고 싶은 시·군·구", wishlist_count)
m3.metric("저장한 장소", place_count)
m4.metric("기록이 있는 시·군·구", area_place_count)

tab_map, tab_regions, tab_records, tab_gallery, tab_backup = st.tabs(
    ["🗺️ 여행 지도", "🏙️ 시·군·구 현황", "📝 장소 기록 관리", "📷 사진 갤러리", "💾 백업"]
)

with tab_map:
    st.subheader("OpenStreetMap 여행 지도")
    f1, f2 = st.columns(2)
    selected_province = f1.selectbox(
        "지도 광역자치단체",
        ["전체"] + list(ADMIN_AREAS.keys()),
        key="map_province",
    )
    subregion_options = ["전체"] if selected_province == "전체" else ["전체"] + ADMIN_AREAS[selected_province]
    selected_subregion = f2.selectbox(
        "지도 시·군·구",
        subregion_options,
        key=f"map_subregion_{selected_province}",
    )
    st.info("지도를 클릭하면 아래 새 장소 입력란의 위도와 경도가 자동으로 바뀝니다.")

    map_obj = build_map(area_df, place_df, selected_province, selected_subregion)
    map_output = st_folium(
        map_obj,
        use_container_width=True,
        height=690,
        key=f"travel_map_{selected_province}_{selected_subregion}",
        returned_objects=["last_clicked"],
    )

    clicked = map_output.get("last_clicked") if map_output else None
    if clicked:
        click_pair = (round(float(clicked["lat"]), 7), round(float(clicked["lng"]), 7))
        if st.session_state.get("last_processed_click") != click_pair:
            st.session_state["new_latitude"] = click_pair[0]
            st.session_state["new_longitude"] = click_pair[1]
            st.session_state["last_processed_click"] = click_pair

    st.subheader("새 장소 기록")
    p1, p2 = st.columns(2)
    default_province = selected_province if selected_province != "전체" else "서울특별시"
    new_province = p1.selectbox(
        "광역자치단체 *",
        list(ADMIN_AREAS.keys()),
        index=list(ADMIN_AREAS.keys()).index(default_province),
        key="new_province",
    )
    new_subregion = p2.selectbox(
        "시·군·구 *",
        ADMIN_AREAS[new_province],
        key=f"new_subregion_{new_province}",
    )

    default_lat, default_lon = PROVINCE_CENTERS[new_province]
    if "new_latitude" not in st.session_state:
        st.session_state["new_latitude"] = float(default_lat)
    if "new_longitude" not in st.session_state:
        st.session_state["new_longitude"] = float(default_lon)

    with st.form("add_place_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        place_name = c1.text_input("장소명 *", placeholder="예: 안동찜닭 골목")
        category = c2.selectbox("카테고리 *", CATEGORY_OPTIONS)
        visit_date_value = c3.date_input("방문일", value=date.today())

        c4, c5 = st.columns([1, 3])
        rating = c4.slider("평점", 1, 5, 4)
        review = c5.text_input(
            "한줄평 *",
            placeholder="예: 골목 분위기와 푸짐한 양이 인상적이었던 곳",
            max_chars=120,
        )

        lat_col, lon_col = st.columns(2)
        latitude = lat_col.number_input(
            "위도",
            min_value=32.0,
            max_value=39.5,
            format="%.7f",
            key="new_latitude",
        )
        longitude = lon_col.number_input(
            "경도",
            min_value=124.0,
            max_value=132.0,
            format="%.7f",
            key="new_longitude",
        )

        new_photos = st.file_uploader(
            "장소 사진 (선택 · 최대 8장 · 장당 10MB)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="첫 번째 사진이 자동으로 대표사진이 됩니다.",
        )
        submitted = st.form_submit_button("📍 지도에 장소 저장", use_container_width=True)
        if submitted:
            if not place_name.strip() or not review.strip():
                st.error("장소명과 한줄평을 모두 입력해 주세요.")
            else:
                new_place_id = add_place(
                    region=new_province,
                    city=new_subregion,
                    place_name=place_name,
                    category=category,
                    visit_date=visit_date_value.isoformat(),
                    rating=rating,
                    review=review,
                    latitude=latitude,
                    longitude=longitude,
                )
                uploaded_count = upload_place_photos(new_place_id, list(new_photos or []))
                st.session_state.pop("last_processed_click", None)
                st.success(
                    f"장소가 저장되었습니다. 사진 {uploaded_count}장도 함께 저장했습니다."
                    if uploaded_count else
                    "장소가 저장되었고 해당 시·군·구가 '가본 곳'으로 변경되었습니다."
                )
                st.rerun()

with tab_regions:
    st.subheader("시·군·구별 방문 상태")
    status_province = st.selectbox(
        "광역자치단체 선택",
        list(ADMIN_AREAS.keys()),
        key="status_province",
    )

    province_status = load_area_status(status_province)
    province_places = load_places()
    if province_places.empty:
        counts = pd.DataFrame(columns=["subregion", "저장 장소 수"])
    else:
        counts = (
            province_places[province_places["region"] == status_province]
            .groupby("city", as_index=False)
            .size()
            .rename(columns={"city": "subregion", "size": "저장 장소 수"})
        )

    editor_df = province_status[["province", "subregion", "status"]].merge(
        counts,
        how="left",
        on="subregion",
    )
    editor_df["저장 장소 수"] = editor_df["저장 장소 수"].fillna(0).astype(int)

    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        disabled=["province", "subregion", "저장 장소 수"],
        column_config={
            "province": st.column_config.TextColumn("광역자치단체"),
            "subregion": st.column_config.TextColumn("시·군·구"),
            "status": st.column_config.SelectboxColumn(
                "방문 상태",
                options=STATUS_OPTIONS,
                required=True,
            ),
            "저장 장소 수": st.column_config.NumberColumn("저장 장소 수", format="%d"),
        },
        key=f"area_editor_{status_province}",
    )

    if st.button("시·군·구 상태 저장", type="primary", use_container_width=True):
        update_area_statuses(edited_df[["province", "subregion", "status"]])
        st.success(f"{status_province}의 방문 상태를 저장했습니다.")
        st.rerun()

    visited, wishlist, total = province_summary(load_area_status(), status_province)
    st.progress(visited / total if total else 0.0, text=f"방문 완료 {visited}/{total} · 가고 싶은 곳 {wishlist}")

with tab_records:
    st.subheader("저장한 장소 검색·수정·삭제")
    current_places = load_places()

    if current_places.empty:
        st.warning("아직 저장한 장소가 없습니다.")
    else:
        f1, f2, f3, f4 = st.columns(4)
        region_filter = f1.multiselect(
            "광역 필터",
            options=sorted(current_places["region"].unique()),
        )
        city_filter_options = sorted(
            current_places.loc[
                current_places["region"].isin(region_filter) if region_filter else current_places.index == current_places.index,
                "city",
            ].dropna().unique()
        )
        city_filter = f2.multiselect("시·군·구 필터", options=city_filter_options)
        category_filter = f3.multiselect(
            "카테고리 필터",
            options=sorted(current_places["category"].unique()),
        )
        keyword = f4.text_input("검색", placeholder="장소명·한줄평")

        filtered_df = current_places.copy()
        if region_filter:
            filtered_df = filtered_df[filtered_df["region"].isin(region_filter)]
        if city_filter:
            filtered_df = filtered_df[filtered_df["city"].isin(city_filter)]
        if category_filter:
            filtered_df = filtered_df[filtered_df["category"].isin(category_filter)]
        if keyword.strip():
            mask = (
                filtered_df["place_name"].str.contains(keyword, case=False, na=False)
                | filtered_df["one_line_review"].str.contains(keyword, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        display_df = filtered_df[
            ["id", "visit_date", "region", "city", "place_name", "category", "rating", "one_line_review"]
        ].rename(
            columns={
                "id": "ID",
                "visit_date": "방문일",
                "region": "광역자치단체",
                "city": "시·군·구",
                "place_name": "장소명",
                "category": "카테고리",
                "rating": "평점",
                "one_line_review": "한줄평",
            }
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        if filtered_df.empty:
            st.info("현재 필터에 해당하는 기록이 없습니다.")
        else:
            with st.expander("✏️ 선택 기록 수정", expanded=True):
                edit_id = st.selectbox(
                    "수정할 기록",
                    options=filtered_df["id"].tolist(),
                    format_func=lambda x: (
                        f"#{x} · "
                        f"{filtered_df.loc[filtered_df['id'] == x, 'place_name'].iloc[0]} · "
                        f"{filtered_df.loc[filtered_df['id'] == x, 'city'].iloc[0]}"
                    ),
                    key="edit_record_id",
                )
                record = current_places[current_places["id"] == edit_id].iloc[0]

                ep1, ep2 = st.columns(2)
                edit_province = ep1.selectbox(
                    "수정 광역자치단체",
                    list(ADMIN_AREAS.keys()),
                    index=list(ADMIN_AREAS.keys()).index(record["region"])
                    if record["region"] in ADMIN_AREAS
                    else 0,
                    key=f"edit_province_{edit_id}",
                )
                edit_city_options = ADMIN_AREAS[edit_province].copy()
                old_city = str(record["city"])
                if edit_province == record["region"] and old_city not in edit_city_options:
                    edit_city_options = [old_city] + edit_city_options
                edit_city = ep2.selectbox(
                    "수정 시·군·구",
                    edit_city_options,
                    index=edit_city_options.index(old_city) if old_city in edit_city_options else 0,
                    key=f"edit_city_{edit_id}_{edit_province}",
                )

                with st.form(f"edit_place_form_{edit_id}"):
                    e1, e2, e3 = st.columns([2, 1, 1])
                    edit_name = e1.text_input("장소명 *", value=str(record["place_name"]))
                    edit_category = e2.selectbox(
                        "카테고리 *",
                        CATEGORY_OPTIONS,
                        index=CATEGORY_OPTIONS.index(record["category"])
                        if record["category"] in CATEGORY_OPTIONS
                        else len(CATEGORY_OPTIONS) - 1,
                    )
                    edit_date = e3.date_input("방문일", value=parse_date(record["visit_date"]))

                    e4, e5 = st.columns([1, 3])
                    edit_rating = e4.slider("평점", 1, 5, int(record["rating"]))
                    edit_review = e5.text_input(
                        "한줄평 *",
                        value=str(record["one_line_review"]),
                        max_chars=120,
                    )

                    e6, e7 = st.columns(2)
                    edit_lat = e6.number_input(
                        "위도",
                        min_value=32.0,
                        max_value=39.5,
                        value=float(record["latitude"]),
                        format="%.7f",
                    )
                    edit_lon = e7.number_input(
                        "경도",
                        min_value=124.0,
                        max_value=132.0,
                        value=float(record["longitude"]),
                        format="%.7f",
                    )

                    update_submitted = st.form_submit_button(
                        "수정 내용 저장",
                        type="primary",
                        use_container_width=True,
                    )
                    if update_submitted:
                        if not edit_name.strip() or not edit_review.strip():
                            st.error("장소명과 한줄평을 모두 입력해 주세요.")
                        else:
                            update_place(
                                place_id=int(edit_id),
                                region=edit_province,
                                city=edit_city,
                                place_name=edit_name,
                                category=edit_category,
                                visit_date=edit_date.isoformat(),
                                rating=edit_rating,
                                review=edit_review,
                                latitude=edit_lat,
                                longitude=edit_lon,
                            )
                            st.success("장소 기록을 수정했습니다.")
                            st.rerun()

            with st.expander("🗑️ 선택 기록 삭제"):
                delete_id = st.selectbox(
                    "삭제할 기록",
                    options=filtered_df["id"].tolist(),
                    format_func=lambda x: (
                        f"#{x} · {filtered_df.loc[filtered_df['id'] == x, 'place_name'].iloc[0]}"
                    ),
                    key="delete_record_id",
                )
                confirm = st.checkbox("삭제 내용을 확인했습니다.", key="delete_confirm")
                if st.button("선택 기록 삭제", type="primary", disabled=not confirm):
                    delete_place(int(delete_id))
                    st.success("기록을 삭제했습니다.")
                    st.rerun()


with tab_gallery:
    st.subheader("장소별 사진 갤러리")
    gallery_places = load_places()
    if gallery_places.empty:
        st.warning("먼저 장소 기록을 추가해 주세요.")
    else:
        g1, g2 = st.columns([2, 1])
        gallery_place_id = g1.selectbox(
            "갤러리를 볼 장소",
            options=gallery_places["id"].tolist(),
            format_func=lambda x: (
                f"#{x} · {gallery_places.loc[gallery_places['id'] == x, 'place_name'].iloc[0]} · "
                f"{gallery_places.loc[gallery_places['id'] == x, 'city'].iloc[0]}"
            ),
            key="gallery_place_id",
        )
        selected_place = gallery_places[gallery_places["id"] == gallery_place_id].iloc[0]
        g2.metric("현재 사진", len(load_place_photos(int(gallery_place_id))))
        st.caption(
            f"{selected_place['region']} · {selected_place['city']} · "
            f"{selected_place['place_name']}"
        )

        with st.form(f"gallery_upload_{gallery_place_id}", clear_on_submit=True):
            gallery_uploads = st.file_uploader(
                "사진 추가",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                help="한 번에 최대 8장, 각 파일은 10MB 이하입니다.",
                key=f"gallery_files_{gallery_place_id}",
            )
            upload_submit = st.form_submit_button(
                "선택한 사진 업로드",
                type="primary",
                use_container_width=True,
            )
            if upload_submit:
                try:
                    count = upload_place_photos(int(gallery_place_id), list(gallery_uploads or []))
                    if count:
                        st.success(f"사진 {count}장을 업로드했습니다.")
                        st.rerun()
                    else:
                        st.warning("업로드할 사진을 선택해 주세요.")
                except Exception as exc:
                    st.error("사진 업로드에 실패했습니다.")
                    st.code(str(exc))

        photos_df = load_place_photos(int(gallery_place_id))
        if photos_df.empty:
            st.info("이 장소에는 아직 사진이 없습니다.")
        else:
            st.divider()
            columns = st.columns(3)
            for index, photo in enumerate(photos_df.itertuples(index=False)):
                with columns[index % 3]:
                    try:
                        photo_url = signed_photo_url(str(photo.storage_path))
                        if photo_url:
                            st.image(
                                photo_url,
                                caption=("대표사진 · " if bool(photo.is_cover) else "")
                                + (str(photo.caption).strip() or str(photo.original_name)),
                                use_container_width=True,
                            )
                        else:
                            st.warning("사진 URL을 만들지 못했습니다.")
                    except Exception as exc:
                        st.warning(f"사진을 불러오지 못했습니다: {exc}")

                    with st.expander("사진 정보 수정·삭제"):
                        with st.form(f"photo_meta_{photo.id}"):
                            caption = st.text_input(
                                "사진 설명",
                                value=str(photo.caption or ""),
                                max_chars=150,
                            )
                            is_cover = st.checkbox("대표사진으로 지정", value=bool(photo.is_cover))
                            save_photo = st.form_submit_button("사진 정보 저장")
                            if save_photo:
                                update_photo_metadata(
                                    int(photo.id), caption, is_cover, int(gallery_place_id)
                                )
                                st.success("사진 정보를 저장했습니다.")
                                st.rerun()
                        delete_confirm = st.checkbox(
                            "이 사진을 삭제합니다.", key=f"photo_delete_confirm_{photo.id}"
                        )
                        if st.button(
                            "사진 삭제",
                            disabled=not delete_confirm,
                            key=f"photo_delete_{photo.id}",
                        ):
                            try:
                                delete_photo(int(photo.id))
                                st.success("사진을 삭제했습니다.")
                                st.rerun()
                            except Exception as exc:
                                st.error("사진 삭제에 실패했습니다.")
                                st.code(str(exc))

with tab_backup:
    st.subheader("백업 및 기존 SQLite 이전")
    current_places = load_places()

    st.download_button(
        "📥 전체 장소 기록 CSV 다운로드",
        data=current_places.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"travel_places_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "📥 시·군·구 방문 상태 CSV 다운로드",
        data=load_area_status().to_csv(index=False).encode("utf-8-sig"),
        file_name=f"travel_area_status_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.success("현재 장소 기록과 방문 상태는 Supabase PostgreSQL에 영구 저장됩니다.")

    st.divider()
    st.subheader("기존 SQLite 데이터 가져오기")
    if DB_PATH.exists():
        st.caption(
            "기존 `travel_log.db`의 방문 상태와 장소 기록을 Supabase로 옮깁니다. "
            "같은 SQLite ID는 다시 실행해도 중복 생성되지 않습니다."
        )
        migration_confirm = st.checkbox(
            "기존 SQLite 데이터를 Supabase로 가져옵니다.",
            key="sqlite_migration_confirm",
        )
        if st.button(
            "SQLite → Supabase 이전 실행",
            type="primary",
            disabled=not migration_confirm,
            use_container_width=True,
        ):
            try:
                area_count, migrated_place_count = migrate_sqlite_to_supabase()
                st.success(
                    f"이전 완료: 방문 상태 {area_count}개, 장소 기록 {migrated_place_count}개"
                )
                st.rerun()
            except Exception as exc:
                st.error("SQLite 데이터 이전 중 오류가 발생했습니다.")
                st.code(str(exc))
    else:
        st.info(
            "현재 프로젝트 폴더에 `travel_log.db`가 없습니다. 기존 데이터가 없다면 정상입니다."
        )

st.caption("개인 여행 기록 v4 · OpenStreetMap + Streamlit + Supabase Storage 사진 갤러리")
