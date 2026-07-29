from __future__ import annotations

import html
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Fullscreen, MarkerCluster
from streamlit_folium import st_folium

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "travel_log.db"

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


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def canonical_subregion(province: str, raw_city: str) -> Optional[str]:
    """기존 자유 입력 도시명을 새 시·군·구 목록에 가능한 범위에서 연결합니다."""
    raw = (raw_city or "").strip()
    options = ADMIN_AREAS.get(province, [])
    if raw in options:
        return raw
    for option in options:
        if raw.startswith(option) or option in raw:
            return option
    return None


def init_db() -> None:
    with get_conn() as conn:
        # 구버전 호환용 테이블은 유지합니다.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS region_status (
                region TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT '미방문',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS area_status (
                province TEXT NOT NULL,
                subregion TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '미방문',
                updated_at TEXT NOT NULL,
                PRIMARY KEY (province, subregion)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT NOT NULL,
                city TEXT NOT NULL,
                place_name TEXT NOT NULL,
                category TEXT NOT NULL,
                visit_date TEXT,
                rating INTEGER NOT NULL DEFAULT 3,
                one_line_review TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        ensure_column(conn, "places", "updated_at", "TEXT")

        now = datetime.now().isoformat(timespec="seconds")
        for province, subregions in ADMIN_AREAS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO region_status(region, status, updated_at)
                VALUES (?, '미방문', ?)
                """,
                (province, now),
            )
            for subregion in subregions:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO area_status(province, subregion, status, updated_at)
                    VALUES (?, ?, '미방문', ?)
                    """,
                    (province, subregion, now),
                )

        # 구버전의 장소 기록이 있으면 일치하는 시·군·구만 자동으로 '가본 곳' 처리합니다.
        legacy_places = conn.execute("SELECT region, city FROM places").fetchall()
        for row in legacy_places:
            matched = canonical_subregion(row["region"], row["city"])
            if matched:
                conn.execute(
                    """
                    UPDATE area_status
                    SET status = '가본 곳', updated_at = ?
                    WHERE province = ? AND subregion = ? AND status = '미방문'
                    """,
                    (now, row["region"], matched),
                )
        conn.commit()


def load_area_status(province: Optional[str] = None) -> pd.DataFrame:
    query = "SELECT province, subregion, status, updated_at FROM area_status"
    params: tuple[object, ...] = ()
    if province:
        query += " WHERE province = ?"
        params = (province,)
    query += " ORDER BY province, subregion"
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params)


def update_area_status(province: str, subregion: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO area_status(province, subregion, status, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(province, subregion) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (province, subregion, status, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def update_area_statuses(rows: pd.DataFrame) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    payload = [
        (str(row.province), str(row.subregion), str(row.status), now)
        for row in rows.itertuples(index=False)
    ]
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO area_status(province, subregion, status, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(province, subregion) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            payload,
        )
        conn.commit()


def load_places() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            """
            SELECT id, region, city, place_name, category, visit_date, rating,
                   one_line_review, latitude, longitude, created_at,
                   COALESCE(updated_at, created_at) AS updated_at
            FROM places
            ORDER BY COALESCE(visit_date, created_at) DESC, id DESC
            """,
            conn,
        )


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
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO places(
                region, city, place_name, category, visit_date, rating,
                one_line_review, latitude, longitude, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                region, city, place_name.strip(), category, visit_date,
                int(rating), review.strip(), float(latitude), float(longitude), now, now,
            ),
        )
        conn.commit()
    update_area_status(region, city, "가본 곳")


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
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE places
            SET region = ?, city = ?, place_name = ?, category = ?, visit_date = ?,
                rating = ?, one_line_review = ?, latitude = ?, longitude = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                region, city, place_name.strip(), category, visit_date, int(rating),
                review.strip(), float(latitude), float(longitude),
                datetime.now().isoformat(timespec="seconds"), int(place_id),
            ),
        )
        conn.commit()
    update_area_status(region, city, "가본 곳")


def delete_place(place_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM places WHERE id = ?", (int(place_id),))
        conn.commit()


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


def parse_date(value: object) -> date:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return date.today()
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return date.today()


init_db()

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

tab_map, tab_regions, tab_records, tab_backup = st.tabs(
    ["🗺️ 여행 지도", "🏙️ 시·군·구 현황", "📝 장소 기록 관리", "💾 백업"]
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

        submitted = st.form_submit_button("📍 지도에 장소 저장", use_container_width=True)
        if submitted:
            if not place_name.strip() or not review.strip():
                st.error("장소명과 한줄평을 모두 입력해 주세요.")
            else:
                add_place(
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
                st.session_state.pop("last_processed_click", None)
                st.success("장소가 저장되었고 해당 시·군·구가 '가본 곳'으로 변경되었습니다.")
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

with tab_backup:
    st.subheader("CSV 백업")
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

    st.warning(
        "Streamlit Community Cloud의 로컬 SQLite 파일은 앱 재부팅·재배포 시 유실될 수 있습니다. "
        "장기 보관용 배포에서는 Supabase 같은 외부 DB 연결을 권장합니다."
    )

st.caption("개인 여행 기록 v2 · OpenStreetMap + Streamlit + Folium + SQLite")
