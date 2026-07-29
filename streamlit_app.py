from __future__ import annotations

import html
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "travel_log.db"

REGIONS = {
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

STATUS_OPTIONS = ["가본 곳", "가고 싶은 곳", "미방문"]
CATEGORY_OPTIONS = ["음식점", "카페", "관광명소", "숙소", "쇼핑", "자연", "기타"]

STATUS_COLORS = {
    "가본 곳": "#2E8B57",
    "가고 싶은 곳": "#F4A261",
    "미방문": "#B8BDC7",
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
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem;}
    .travel-title {font-size: 2.1rem; font-weight: 800; margin-bottom: .1rem;}
    .travel-sub {color: #6b7280; margin-bottom: 1rem;}
    .metric-card {
        border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px 16px;
        background: rgba(255,255,255,.04);
    }
    div[data-testid="stForm"] {border-radius: 14px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
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
        now = datetime.now().isoformat(timespec="seconds")
        for region in REGIONS:
            conn.execute(
                """
                INSERT OR IGNORE INTO region_status(region, status, updated_at)
                VALUES (?, '미방문', ?)
                """,
                (region, now),
            )
        conn.commit()


def load_region_status() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT region, status, updated_at FROM region_status ORDER BY region",
            conn,
        )


def update_region_status(region: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO region_status(region, status, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(region) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (region, status, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def load_places() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT id, region, city, place_name, category, visit_date, rating,
                   one_line_review, latitude, longitude, created_at
            FROM places
            ORDER BY COALESCE(visit_date, created_at) DESC, id DESC
            """,
            conn,
        )
    return df


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
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO places(
                region, city, place_name, category, visit_date, rating,
                one_line_review, latitude, longitude, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                region, city.strip(), place_name.strip(), category, visit_date,
                int(rating), review.strip(), float(latitude), float(longitude),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def delete_place(place_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM places WHERE id = ?", (int(place_id),))
        conn.commit()


def safe(value: object) -> str:
    return html.escape("" if value is None else str(value))


def build_map(
    region_df: pd.DataFrame,
    place_df: pd.DataFrame,
    selected_region: str,
) -> folium.Map:
    center = REGIONS.get(selected_region, (36.4, 127.8))
    zoom = 8 if selected_region != "전체" else 7

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # 광역자치단체 상태 마커
    status_lookup = dict(zip(region_df["region"], region_df["status"]))
    for region, (lat, lon) in REGIONS.items():
        status = status_lookup.get(region, "미방문")
        folium.CircleMarker(
            location=[lat, lon],
            radius=9,
            color=STATUS_COLORS[status],
            fill=True,
            fill_color=STATUS_COLORS[status],
            fill_opacity=0.85,
            weight=2,
            tooltip=f"{region} · {status}",
            popup=folium.Popup(
                f"<b>{safe(region)}</b><br>{safe(status)}",
                max_width=240,
            ),
        ).add_to(m)

    # 장소 기록 마커
    cluster = MarkerCluster(name="나의 장소 기록").add_to(m)
    filtered = place_df
    if selected_region != "전체" and not place_df.empty:
        filtered = place_df[place_df["region"] == selected_region]

    for row in filtered.itertuples(index=False):
        visit_text = row.visit_date if pd.notna(row.visit_date) and row.visit_date else "날짜 미입력"
        stars = "★" * int(row.rating) + "☆" * (5 - int(row.rating))
        popup_html = f"""
        <div style="width:240px">
          <b>{safe(row.place_name)}</b><br>
          {safe(row.region)} · {safe(row.city)}<br>
          {safe(row.category)} · {safe(visit_text)}<br>
          <span style="color:#d97706">{stars}</span><br>
          <hr style="margin:6px 0">
          {safe(row.one_line_review)}
        </div>
        """
        folium.Marker(
            location=[row.latitude, row.longitude],
            tooltip=f"{row.place_name} · {row.category}",
            popup=folium.Popup(popup_html, max_width=280),
            icon=folium.Icon(
                color="blue",
                icon=CATEGORY_ICONS.get(row.category, "map-marker"),
                prefix="fa",
            ),
        ).add_to(cluster)

    folium.LayerControl(collapsed=True).add_to(m)
    return m


init_db()

st.markdown('<div class="travel-title">🧭 나의 대한민국 여행 기록</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="travel-sub">도시의 방문 상태를 정리하고, 지도에 음식점·관광명소·숙소 기록을 남겨보세요.</div>',
    unsafe_allow_html=True,
)

region_df = load_region_status()
place_df = load_places()

visited_count = int((region_df["status"] == "가본 곳").sum())
wishlist_count = int((region_df["status"] == "가고 싶은 곳").sum())
place_count = len(place_df)
region_place_count = int(place_df["region"].nunique()) if not place_df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("가본 지역", f"{visited_count} / {len(REGIONS)}")
m2.metric("가고 싶은 지역", wishlist_count)
m3.metric("저장한 장소", place_count)
m4.metric("기록이 있는 지역", region_place_count)

tab_map, tab_regions, tab_records, tab_backup = st.tabs(
    ["🗺️ 여행 지도", "🏙️ 도시별 현황", "📝 장소 기록 관리", "💾 백업"]
)

with tab_map:
    filter_col, info_col = st.columns([1, 2])
    with filter_col:
        selected_region = st.selectbox(
            "지도에 표시할 지역",
            ["전체"] + list(REGIONS.keys()),
            key="map_region",
        )
    with info_col:
        st.info("지도를 클릭하면 아래 입력란의 위도·경도에 해당 위치가 반영됩니다.")

    map_obj = build_map(region_df, place_df, selected_region)
    map_output = st_folium(
        map_obj,
        use_container_width=True,
        height=600,
        key=f"travel_map_{selected_region}",
        returned_objects=["last_clicked"],
    )

    clicked = map_output.get("last_clicked") if map_output else None
    if clicked:
        st.session_state["clicked_lat"] = float(clicked["lat"])
        st.session_state["clicked_lon"] = float(clicked["lng"])

    st.subheader("새 장소 기록")
    default_region = selected_region if selected_region != "전체" else "서울특별시"
    default_lat, default_lon = REGIONS[default_region]
    current_lat = st.session_state.get("clicked_lat", default_lat)
    current_lon = st.session_state.get("clicked_lon", default_lon)

    with st.form("add_place_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        region = c1.selectbox(
            "광역자치단체 *",
            list(REGIONS.keys()),
            index=list(REGIONS.keys()).index(default_region),
        )
        city = c2.text_input("도시·구·군 *", placeholder="예: 전주시 완산구")
        category = c3.selectbox("카테고리 *", CATEGORY_OPTIONS)

        c4, c5, c6 = st.columns([2, 1, 1])
        place_name = c4.text_input("장소명 *", placeholder="예: 한국집")
        visit_date_value = c5.date_input("방문일", value=date.today())
        rating = c6.slider("평점", 1, 5, 4)

        review = st.text_input(
            "한줄평 *",
            placeholder="예: 육회비빔밥과 밑반찬이 인상적이었던 곳",
            max_chars=120,
        )

        lat_col, lon_col = st.columns(2)
        latitude = lat_col.number_input(
            "위도",
            min_value=32.0,
            max_value=39.5,
            value=float(current_lat),
            format="%.6f",
        )
        longitude = lon_col.number_input(
            "경도",
            min_value=124.0,
            max_value=132.0,
            value=float(current_lon),
            format="%.6f",
        )

        submitted = st.form_submit_button("📍 지도에 장소 저장", use_container_width=True)
        if submitted:
            if not city.strip() or not place_name.strip() or not review.strip():
                st.error("도시·구·군, 장소명, 한줄평을 모두 입력해 주세요.")
            else:
                add_place(
                    region=region,
                    city=city,
                    place_name=place_name,
                    category=category,
                    visit_date=visit_date_value.isoformat(),
                    rating=rating,
                    review=review,
                    latitude=latitude,
                    longitude=longitude,
                )
                update_region_status(region, "가본 곳")
                st.session_state.pop("clicked_lat", None)
                st.session_state.pop("clicked_lon", None)
                st.success("장소가 저장되었습니다.")
                st.rerun()

with tab_regions:
    st.subheader("광역자치단체 방문 상태")
    st.caption("상태를 바꾸면 지도 색상과 통계에 바로 반영됩니다.")

    status_lookup = dict(zip(region_df["region"], region_df["status"]))
    for start in range(0, len(REGIONS), 3):
        cols = st.columns(3)
        region_names = list(REGIONS.keys())[start:start + 3]
        for col, region_name in zip(cols, region_names):
            with col:
                current_status = status_lookup.get(region_name, "미방문")
                new_status = st.selectbox(
                    region_name,
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(current_status),
                    key=f"status_{region_name}",
                )
                if new_status != current_status:
                    update_region_status(region_name, new_status)
                    st.rerun()

    st.divider()
    summary = (
        load_region_status()
        .groupby("status", as_index=False)
        .size()
        .rename(columns={"size": "지역 수"})
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

with tab_records:
    st.subheader("저장한 장소")
    current_places = load_places()

    if current_places.empty:
        st.warning("아직 저장한 장소가 없습니다.")
    else:
        f1, f2, f3 = st.columns(3)
        region_filter = f1.multiselect(
            "지역 필터",
            options=sorted(current_places["region"].unique()),
        )
        category_filter = f2.multiselect(
            "카테고리 필터",
            options=sorted(current_places["category"].unique()),
        )
        keyword = f3.text_input("검색", placeholder="장소명·도시·한줄평")

        filtered_df = current_places.copy()
        if region_filter:
            filtered_df = filtered_df[filtered_df["region"].isin(region_filter)]
        if category_filter:
            filtered_df = filtered_df[filtered_df["category"].isin(category_filter)]
        if keyword.strip():
            mask = (
                filtered_df["place_name"].str.contains(keyword, case=False, na=False)
                | filtered_df["city"].str.contains(keyword, case=False, na=False)
                | filtered_df["one_line_review"].str.contains(keyword, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        display_cols = [
            "id", "visit_date", "region", "city", "place_name",
            "category", "rating", "one_line_review"
        ]
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("기록 삭제"):
            delete_id = st.selectbox(
                "삭제할 기록",
                options=filtered_df["id"].tolist(),
                format_func=lambda x: (
                    f"#{x} · "
                    f"{filtered_df.loc[filtered_df['id'] == x, 'place_name'].iloc[0]}"
                ),
            )
            confirm = st.checkbox("삭제 내용을 확인했습니다.")
            if st.button("선택 기록 삭제", type="primary", disabled=not confirm):
                delete_place(int(delete_id))
                st.success("기록을 삭제했습니다.")
                st.rerun()

with tab_backup:
    st.subheader("CSV 백업 및 복원")
    current_places = load_places()

    csv_data = current_places.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 전체 장소 기록 CSV 다운로드",
        data=csv_data,
        file_name=f"travel_places_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    region_csv = load_region_status().to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 도시 방문 상태 CSV 다운로드",
        data=region_csv,
        file_name=f"travel_region_status_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.warning(
        "Streamlit Community Cloud의 로컬 SQLite 파일은 앱 재부팅·재배포 시 "
        "유실될 수 있습니다. 장기 보관용 공개 배포에서는 Supabase 같은 외부 DB 연결을 권장합니다."
    )

st.caption("개인 여행 기록용 MVP · Python + Streamlit + Folium + SQLite")
