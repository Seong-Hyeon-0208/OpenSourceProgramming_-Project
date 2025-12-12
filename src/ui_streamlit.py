
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
from scheduler import generate_schedule

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def init_state() -> None:
    if "subjects" not in st.session_state:
        today = date.today()
        st.session_state["subjects"] = [
            {"name": "선형대수학", "weekly": 4.0, "exam": today + timedelta(days=21)},
            {"name": "데이터통신", "weekly": 3.0, "exam": today + timedelta(days=14)},
            {"name": "컴퓨터구조", "weekly": 3.0, "exam": today + timedelta(days=28)},
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
        schedule = generate_schedule(cfg)

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
