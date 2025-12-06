
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from .models import UserConfig, ScheduleDay, StudyBlock, Subject


def _subject_daily_demand(subject: Subject, horizon_days: int) -> float:
    """
    매우 단순화된 수요 모델:
    - weekly_target_hours 를 horizon_days 기준으로 환산
    """
    daily = subject.weekly_target_hours / 7.0
    return daily * horizon_days


def _subject_weight(subject: Subject, day: date) -> float:
    """
    과목별 우선순위 가중치를 계산.
    - priority(1~5)
    - 시험이 가까울수록 가중치 증가
    """
    base = max(subject.priority, 1)

    if subject.exam_date:
        days_to_exam = (subject.exam_date - day).days
        if days_to_exam <= 0:
            urgency = 2.0
        else:
            urgency = 1.0 + min(1.5, 10.0 / max(days_to_exam, 1))
    else:
        urgency = 1.0

    return base * urgency


def generate_initial_schedule(
    config: UserConfig,
    start_date: date | None = None,
) -> List[ScheduleDay]:
    """
    주어진 설정을 바탕으로 다음 planning_horizon_days 동안의
    초기 학습 스케줄을 생성한다.
    """
    if start_date is None:
        start_date = date.today()

    days: List[ScheduleDay] = []
    for d in range(config.planning_horizon_days):
        current = start_date + timedelta(days=d)
        weekday = current.weekday()  # Monday=0
        available = config.daily_available_hours.get(weekday, 0.0)
        days.append(ScheduleDay(date=current, total_available_hours=available))

    # 각 과목별로 horizon 동안 필요한 총 공부량 추정
    subject_remaining = {
        subj.name: _subject_daily_demand(subj, config.planning_horizon_days)
        for subj in config.subjects
    }

    # 날짜별로 순차적으로 시간을 채워 넣기
    for day in days:
        while day.remaining_hours > 0.01:
            # 남은 공부량이 있는 과목만 고려
            candidate_subjects = [
                subj for subj in config.subjects
                if subject_remaining[subj.name] > 0.01
            ]
            if not candidate_subjects:
                break

            # 오늘 기준으로 가장 우선순위가 높은 과목 선택
            best = max(
                candidate_subjects,
                key=lambda s: _subject_weight(s, day.date),
            )

            # 이 과목에 배정할 시간
            block_hours = min(
                config.max_block_hours,
                day.remaining_hours,
                subject_remaining[best.name],
            )

            if block_hours <= 0:
                break

            day.blocks.append(StudyBlock(subject_name=best.name, hours=block_hours))
            subject_remaining[best.name] -= block_hours

    return days
