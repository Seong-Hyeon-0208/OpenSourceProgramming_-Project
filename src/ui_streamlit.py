"""
실행:
  cd src
  streamlit run ui_streamlit.py
"""

from __future__ import annotations

from datetime import date, timedelta
import hashlib

import pandas as pd
import streamlit as st

from models import Subject, TimeBlock, UserConfig
from scheduler import generate_weekly_grid_schedule

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

# =========================
# 과목 색 이모지 매핑
# =========================
SUBJECT_EMOJIS = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬛", "⬜"]

def emoji_for_subject(name: str) -> str:
    """
    과목명 -> 항상 동일한 색 이모지로 매핑
    (앱 재실행/순서 변경에도 유지)
    """
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    return SUBJECT_EMOJIS[h % len(SUBJECT_EMOJIS)]


# =========================
# Utilities
# =========================
def hhmm_to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def min_to_hhmm(mm: int) -> str:
    return f"{mm // 60:02d}:{mm % 60:02d}"


def init_state() -> None:
    if "subjects" not in st.session_state:
        today = date.today()
        st.session_state["subjects"] = [
            {"name": "새 과목1", "weekly": 4.0, "exam": today + timedelta(days=21)},
            {"name": "새 과목2", "weekly": 3.0, "exam": today + timedelta(days=14)},
            {"name": "새 과목3", "weekly": 3.0, "exam": today + timedelta(days=28)},
        ]

    if "busy_blocks" not in st.session_state:
        st.session_state["busy_blocks"] = []

    defaults = {
        "horizon": 7,
        "study_mode": "분배형 (1~2시간)",
        "slot": 30,
        "grid_start": 9,
        "grid_end": 24,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def add_subject():
    st.session_state["subjects"].append(
        {"name": f"새 과목 {len(st.session_state['subjects'])+1}", "weekly": 2.0, "exam": None}
    )


def remove_last_subject():
    if st.session_state["subjects"]:
        st.session_state["subjects"].pop()


def build_config() -> UserConfig:
    subjects = []
    for row in st.session_state["subjects"]:
        if row["name"].strip():
            subjects.append(
                Subject(
                    name=row["name"],
                    weekly_target_hours=float(row["weekly"]),
                    exam_date=row["exam"],
                )
            )

    mode = st.session_state["study_mode"]
    if mode.startswith("장기"):
        min_block, max_block = 2.0, 3.0
    else:
        min_block, max_block = 1.0, 2.0

    busy = [
        TimeBlock(
            weekday=b["weekday"],
            start_min=b["start_min"],
            end_min=b["end_min"],
            label=b["label"],
            kind="busy",
        )
        for b in st.session_state["busy_blocks"]
    ]

    return UserConfig(
        subjects=subjects,
        planning_horizon_days=st.session_state["horizon"],
        min_block_hours=min_block,
        max_block_hours=max_block,
        day_start_hour=st.session_state["grid_start"],
        day_end_hour=st.session_state["grid_end"],
        slot_minutes=st.session_state["slot"],
        busy_blocks=busy,
    )


def render_grid(cfg: UserConfig, blocks: list[TimeBlock]) -> pd.DataFrame:
    slot = cfg.slot_minutes
    start_min = cfg.day_start_hour * 60
    end_min = cfg.day_end_hour * 60

    times = list(range(start_min, end_min, slot))
    idx_map = {t: i for i, t in enumerate(times)}

    grid = {"시간": [min_to_hhmm(t) for t in times]}
    for wd in WEEKDAY_LABELS:
        grid[wd] = [""] * len(times)

    def fill(block: TimeBlock, text: str):
        for t in range(block.start_min, block.end_min, slot):
            if t in idx_map:
                grid[WEEKDAY_LABELS[block.weekday]][idx_map[t]] = text

    # ⛔ 불가능 시간
    for b in blocks:
        if b.kind == "busy":
            fill(b, f"⛔ {b.label}")

    # 🟥🟧🟨… 과목 색 이모지
    for b in blocks:
        if b.kind == "study":
            emoji = emoji_for_subject(b.label)
            fill(b, f"{emoji} {b.label}")

    return pd.DataFrame(grid)


# =========================
# Main App
# =========================
def main():
    st.set_page_config(page_title="Smart Study Scheduler", layout="wide")
    init_state()

    st.title("🗓️ Smart Study Scheduler (과목 색 이모지 버전)")

    # 1) 과목 설정
    st.subheader("1) 과목 설정")
    c1, c2 = st.columns(2)
    c1.button("➕ 과목 추가", on_click=add_subject, key="add_subject")
    c2.button("➖ 마지막 과목 삭제", on_click=remove_last_subject, key="remove_subject")

    for i, row in enumerate(st.session_state["subjects"]):
        with st.expander(f"과목 {i+1}: {row['name']}", expanded=(i == 0)):
            row["name"] = st.text_input("과목 이름", row["name"], key=f"name_{i}")
            row["weekly"] = st.number_input("주당 공부 시간", 0.0, 60.0, row["weekly"], 0.5, key=f"week_{i}")
            row["exam"] = st.date_input("시험 날짜", row["exam"], key=f"exam_{i}")

    st.divider()

    # 2) 기간 / 유형
    st.subheader("2) 스케줄 옵션")
    st.slider("기간(일)", 3, 30, key="horizon")
    st.radio("학습 유형", ["장기 몰입형 (2~3시간)", "분배형 (1~2시간)"], key="study_mode")
    st.selectbox("시간 슬롯(분)", [30, 60], key="slot")

    st.divider()

    # 3) 시간 범위
    st.subheader("3) 하루 시간 범위")
    st.number_input("시작(시)", 0, 23, key="grid_start")
    st.number_input("끝(시)", 1, 24, key="grid_end")

    st.divider()

    # 4) 불가능 시간
    st.subheader("4) 공부 불가능 시간")
    with st.form("busy_form", clear_on_submit=True):
        w = st.selectbox("요일", range(7), format_func=lambda x: WEEKDAY_LABELS[x])
        s = st.text_input("시작(HH:MM)", "12:00")
        e = st.text_input("끝(HH:MM)", "13:00")
        label = st.text_input("이름", "점심")
        if st.form_submit_button("추가"):
            st.session_state["busy_blocks"].append(
                {"weekday": w, "start_min": hhmm_to_min(s), "end_min": hhmm_to_min(e), "label": label}
            )

    for i, b in enumerate(st.session_state["busy_blocks"]):
        cols = st.columns([1, 1, 1, 3, 1])
        cols[0].write(WEEKDAY_LABELS[b["weekday"]])
        cols[1].write(min_to_hhmm(b["start_min"]))
        cols[2].write(min_to_hhmm(b["end_min"]))
        cols[3].write(b["label"])
        if cols[4].button("삭제", key=f"del_busy_{i}"):
            st.session_state["busy_blocks"].pop(i)
            st.rerun()

    st.divider()

    # 5) 생성
    if st.button("📅 스케줄 생성", type="primary", key="generate"):
        cfg = build_config()
        blocks = generate_weekly_grid_schedule(cfg, start_date=date.today())
        df = render_grid(cfg, blocks)

        st.subheader("✅ 주간 시간표")
        st.dataframe(df, use_container_width=True)

        # 과목 색 legend
        st.subheader("🎨 과목 구분")
        legend = "  ".join(
            f"{emoji_for_subject(s.name)} {s.name}" for s in cfg.subjects
        )
        st.markdown(legend)

        st.download_button(
            "CSV 다운로드",
            df.to_csv(index=False).encode("utf-8-sig"),
            "weekly_schedule.csv",
            "text/csv",
        )


if __name__ == "__main__":
    main()

