
"""
Streamlit 기반 간단 웹 UI.

실행 방법:
    streamlit run src/ui_streamlit.py
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from models import Subject, UserConfig
from scheduler import generate_initial_schedule


WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def _default_subjects() -> list[Subject]:
    today = date.today()
    return [
        Subject(
            name="선형대수학",
            weekly_target_hours=4.0,
            priority=4,
            exam_date=today + timedelta(days=21),
        ),
        Subject(
            name="데이터통신",
            weekly_target_hours=3.0,
            priority=5,
            exam_date=today + timedelta(days=14),
        ),
        Subject(
            name="컴퓨터구조",
            weekly_target_hours=3.0,
            priority=3,
            exam_date=today + timedelta(days=28),
        ),
    ]


def _subject_input() -> list[Subject]:
    st.subheader("1. 과목 설정")

    if "subjects" not in st.session_state:
        st.session_state["subjects"] = _default_subjects()

    subjects: list[Subject] = st.session_state["subjects"]

    new_subjects: list[Subject] = []
    for idx, subj in enumerate(subjects):
        with st.expander(f"과목 {idx+1}: {subj.name}", expanded=(idx == 0)):
            name = st.text_input("과목 이름", value=subj.name, key=f"name_{idx}")
            weekly_hours = st.number_input(
                "주당 공부 목표 시간 (시간)",
                min_value=0.0,
                max_value=40.0,
                value=float(subj.weekly_target_hours),
                step=0.5,
                key=f"weekly_{idx}",
            )
            priority = st.slider(
                "우선순위 (1=낮음, 5=매우 높음)",
                min_value=1,
                max_value=5,
                value=int(subj.priority),
                key=f"priority_{idx}",
            )
            exam_date = st.date_input(
                "시험 날짜 (선택)",
                value=subj.exam_date,
                key=f"exam_{idx}",
            )
            new_subjects.append(
                Subject(
                    name=name,
                    weekly_target_hours=weekly_hours,
                    priority=priority,
                    exam_date=exam_date,
                )
            )

    st.markdown("---")
    st.write("과목 수를 조절하려면 아래 버튼을 사용하세요.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("과목 추가"):
            new_subjects.append(
                Subject(
                    name=f"새 과목 {len(new_subjects)+1}",
                    weekly_target_hours=2.0,
                    priority=3,
                    exam_date=None,
                )
            )
    with col2:
        if st.button("마지막 과목 삭제") and new_subjects:
            new_subjects.pop()

    st.session_state["subjects"] = new_subjects
    return new_subjects


def _daily_hours_input() -> dict[int, float]:
    st.subheader("2. 요일별 가용 공부 시간")
    daily_hours: dict[int, float] = {}
    for i, label in enumerate(WEEKDAY_LABELS):
        daily_hours[i] = st.number_input(
            f"{label}요일 (시간)",
            min_value=0.0,
            max_value=24.0,
            value=3.0 if i < 5 else 1.0,
            step=0.5,
            key=f"avail_{i}",
        )
    return daily_hours


def main() -> None:
    st.title("📚 Smart Study Scheduler")
    st.write(
        "개인화된 학습 스케줄을 자동으로 생성해 주는 간단한 데모입니다.\n"
        "과목 정보와 요일별 공부 가능 시간을 입력한 뒤, '스케줄 생성' 버튼을 눌러 보세요."
    )

    subjects = _subject_input()
    daily_hours = _daily_hours_input()

    st.subheader("3. 기타 설정")
    horizon = st.slider(
        "며칠치 일정을 생성할까요?",
        min_value=3,
        max_value=21,
        value=7,
    )
    max_block = st.slider(
        "한 번에 연속으로 공부할 최대 시간 (시간)",
        min_value=0.5,
        max_value=4.0,
        value=2.0,
        step=0.5,
    )

    if st.button("📅 스케줄 생성"):
        cfg = UserConfig(
            subjects=subjects,
            daily_available_hours=daily_hours,
            planning_horizon_days=horizon,
            max_block_hours=max_block,
        )
        schedule = generate_initial_schedule(cfg)

        # 표 형태로 요약
        rows = []
        for day in schedule:
            for block in day.blocks:
                rows.append(
                    {
                        "날짜": day.date.isoformat(),
                        "요일": WEEKDAY_LABELS[day.date.weekday()],
                        "과목": block.subject_name,
                        "시간(시간)": block.hours,
                    }
                )
        if rows:
            df = pd.DataFrame(rows)
            st.subheader("생성된 스케줄")
            st.dataframe(df, use_container_width=True)

            # 요일별 총 공부시간 그래프
            st.subheader("요일별 총 공부 시간")
            chart_df = (
                df.groupby(["날짜", "요일"])["시간(시간)"]
                .sum()
                .reset_index()
                .rename(columns={"시간(시간)": "총 공부 시간"})
            )
            st.bar_chart(chart_df.set_index("날짜")["총 공부 시간"])
        else:
            st.info("입력한 조건으로 배정할 수 있는 스케줄이 없습니다. 요일별 가용 시간을 늘려 보세요.")


if __name__ == "__main__":
    main()
