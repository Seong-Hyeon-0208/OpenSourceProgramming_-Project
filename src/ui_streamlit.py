
"""
실행:
  cd src
  streamlit run ui_streamlit.py
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from models import Subject, UserConfig
from scheduler import generate_weekly_grid_schedule

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

from models import TimeBlock
from scheduler import generate_weekly_grid_schedule

def hhmm_to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)

st.subheader("4) 공부 불가능 시간(강의/식사 등) 설정")

if "busy_blocks" not in st.session_state:
    st.session_state["busy_blocks"] = []

with st.form("busy_form", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        w = st.selectbox("요일", options=list(range(7)), format_func=lambda i: WEEKDAY_LABELS[i])
    with c2:
        start = st.text_input("시작(HH:MM)", value="12:00")
    with c3:
        end = st.text_input("끝(HH:MM)", value="13:00")
    with c4:
        label = st.text_input("이름", value="점심")

    submitted = st.form_submit_button("➕ 불가능 시간 추가")
    if submitted:
        st.session_state["busy_blocks"].append({
            "weekday": w,
            "start_min": hhmm_to_min(start),
            "end_min": hhmm_to_min(end),
            "label": label
        })

# 목록 표시 + 삭제
for idx, b in enumerate(st.session_state["busy_blocks"]):
    cols = st.columns([2,2,2,3,1])
    cols[0].write(WEEKDAY_LABELS[b["weekday"]])
    cols[1].write(f'{b["start_min"]//60:02d}:{b["start_min"]%60:02d}')
    cols[2].write(f'{b["end_min"]//60:02d}:{b["end_min"]%60:02d}')
    cols[3].write(b["label"])
    if cols[4].button("삭제", key=f"del_busy_{idx}"):
        st.session_state["busy_blocks"].pop(idx)
        st.rerun()


def init_state() -> None:
    if "subjects" not in st.session_state:
        today = date.today()
        st.session_state["subjects"] = [
            {"name": "과목 이름", "weekly": 4.0, "exam": today + timedelta(days=21)},
            {"name": "과목 이름", "weekly": 3.0, "exam": today + timedelta(days=14)},
            {"name": "과목 이름", "weekly": 3.0, "exam": today + timedelta(days=28)},
        ]
    if "daily_hours" not in st.session_state:
        # 평일 3h, 주말 1h 기본값
        st.session_state["daily_hours"] = {i: (3.0 if i < 5 else 1.0) for i in range(7)}
    if "horizon" not in st.session_state:
        st.session_state["horizon"] = 7
    if "study_mode" not in st.session_state:
        st.session_state["study_mode"] = "분배형 (1~2시간)"


def add_subject() -> None:
    st.session_state["subjects"].append({"name": f"새 과목 {len(st.session_state['subjects'])+1}", "weekly": 2.0, "exam": None})


def remove_last_subject() -> None:
    if st.session_state["subjects"]:
        st.session_state["subjects"].pop()


def build_config() -> UserConfig:
    subjects = []
    for row in st.session_state["subjects"]:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        subjects.append(
            Subject(
                name=name,
                weekly_target_hours=float(row.get("weekly", 0.0)),
                exam_date=row.get("exam"),
            )
        )

    daily = {int(k): float(v) for k, v in st.session_state["daily_hours"].items()}
    horizon = int(st.session_state["horizon"])
    
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
    mode = st.session_state["study_mode"]
    if mode.startswith("장기"):
        min_block, max_block = 2.0, 3.0
    else:
        min_block, max_block = 1.0, 2.0

    return UserConfig(
        subjects=subjects,
        daily_available_hours=daily,
        planning_horizon_days=horizon,
        min_block_hours=min_block,
        max_block_hours=max_block,
        busy_blocks=busy, 
        day_start_hour=9, 
        day_end_hour=24, 
        slot_minutes=30
    )


def main() -> None:
    st.set_page_config(page_title="Smart Study Scheduler", layout="wide")
    init_state()

    st.title("📚 Smart Study Scheduler")
    st.caption("과목/시간/시험일/학습유형(몰입형·분배형)을 기반으로 학습 스케줄을 자동 생성합니다.")

    # 1) 과목 입력 + 추가/삭제
    st.subheader("1) 과목 설정")
    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("➕ 과목 추가"):
            add_subject()
    with colB:
        if st.button("➖ 마지막 과목 삭제"):
            remove_last_subject()

    for i, row in enumerate(st.session_state["subjects"]):
        with st.expander(f"과목 {i+1}: {row.get('name','')}", expanded=(i == 0)):
            row["name"] = st.text_input("과목 이름", value=row.get("name", ""), key=f"subj_name_{i}")
            row["weekly"] = st.number_input(
                "주당 공부 필요 시간(시간)",
                min_value=0.0,
                max_value=60.0,
                value=float(row.get("weekly", 0.0)),
                step=0.5,
                key=f"subj_weekly_{i}",
            )
            row["exam"] = st.date_input(
                "시험 날짜(선택) — 시험 이후에는 스케줄에서 제외",
                value=row.get("exam"),
                key=f"subj_exam_{i}",
            )

    st.divider()

    # 2) 기간 설정 + 학습 유형
    st.subheader("2) 스케줄 기간 & 학습 유형")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state["horizon"] = st.slider(
            "스케줄을 짤 기간(일)",
            min_value=3,
            max_value=30,
            value=int(st.session_state["horizon"]),
        )
    with c2:
        st.session_state["study_mode"] = st.radio(
            "학습 유형",
            options=["장기 몰입형 (2~3시간)", "분배형 (1~2시간)"],
            index=0 if str(st.session_state["study_mode"]).startswith("장기") else 1,
        )

    st.divider()

    # 3) 요일별 가용 시간
    st.subheader("3) 요일별 가용 공부 시간")
    cols = st.columns(7)
    for i, label in enumerate(WEEKDAY_LABELS):
        with cols[i]:
            st.session_state["daily_hours"][i] = st.number_input(
                label,
                min_value=0.0,
                max_value=24.0,
                value=float(st.session_state["daily_hours"].get(i, 0.0)),
                step=0.5,
                key=f"avail_{i}",
            )

    st.divider()

    # 생성 버튼
    if st.button("📅 스케줄 생성", type="primary"):
        cfg = build_config()
        blocks = generate_weekly_grid_schedule(cfg, start_date=date.today())

        rows = []
        for day in schedule:
            for block in day.blocks:
                rows.append(
                    {
                        "날짜": day.date.isoformat(),
                        "요일": WEEKDAY_LABELS[day.date.weekday()],
                        "과목": block.subject_name,
                        "시간(시간)": float(block.hours),
                    }
                )

        if not rows:
            st.warning("생성된 스케줄이 없습니다. 과목/가용 시간/기간 설정을 확인해 주세요.")
            return

        df = pd.DataFrame(rows)
        st.subheader("✅ 생성된 스케줄")
        st.dataframe(df, use_container_width=True)

        st.subheader("📊 날짜별 총 공부 시간")
        daily_sum = df.groupby(["날짜", "요일"])["시간(시간)"].sum().reset_index()
        st.bar_chart(daily_sum.set_index("날짜")["시간(시간)"])

        st.download_button(
            "CSV로 다운로드",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="study_schedule.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()

blocks = generate_weekly_grid_schedule(cfg)

# 30분 슬롯 그리드 생성
slot = cfg.slot_minutes
start_min = cfg.day_start_hour * 60
end_min = cfg.day_end_hour * 60

times = list(range(start_min, end_min, slot))
grid = { "시간": [f"{t//60:02d}:{t%60:02d}" for t in times] }
for i, wd in enumerate(WEEKDAY_LABELS):
    grid[wd] = [""] * len(times)

def fill(block, text):
    for t in range(block.start_min, block.end_min, slot):
        if t in times:
            r = times.index(t)
            grid[WEEKDAY_LABELS[block.weekday]][r] = text

# busy 먼저 채우고, study가 덮어쓰게(or 반대)
for b in blocks:
    text = f"⛔ {b.label}" if b.kind == "busy" else f"📘 {b.label}"
    fill(b, text)

df_grid = pd.DataFrame(grid)
st.subheader("🗓️ 주간 시간표 (가로=요일, 세로=시간)")
st.dataframe(df_grid, use_container_width=True)
