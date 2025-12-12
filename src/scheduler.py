
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from models import UserConfig, ScheduleDay, StudyBlock, Subject


def _subject_daily_demand(subject: Subject, horizon_days: int) -> float:
    """weekly_target_hours를 horizon_days 기준으로 단순 환산."""
    return (subject.weekly_target_hours / 7.0) * horizon_days


def _is_subject_active_on_day(subject: Subject, day: date) -> bool:
    """시험일 이후(시험일 포함 X)는 스케줄에서 제외."""
    if subject.exam_date is None:
        return True
    # 시험일 당일 포함 여부는 과제 조건에 따라 선택 가능.
    # 여기서는 '시험 이후'는 제외라고 했으므로, 시험일 당일은 포함, 다음날부터 제외.
    return day <= subject.exam_date


def generate_schedule(config: UserConfig, start_date: date | None = None) -> List[ScheduleDay]:
    """다음 N일(planning_horizon_days) 동안 학습 스케줄 생성."""
    if start_date is None:
        start_date = date.today()

    # 날짜별 가용 시간
    days: List[ScheduleDay] = []
    for i in range(config.planning_horizon_days):
        d = start_date + timedelta(days=i)
        avail = float(config.daily_available_hours.get(d.weekday(), 0.0))
        days.append(ScheduleDay(date=d, total_available_hours=avail))

    # 과목별 필요 시간(단순 모델)
    remaining = {s.name: _subject_daily_demand(s, config.planning_horizon_days) for s in config.subjects}

    # 라운드로빈 방식 + 시험일 이후 제외
    subj_order = [s for s in config.subjects]

    for day in days:
        # 오늘 가능한 과목만
        active_subjects = [s for s in subj_order if _is_subject_active_on_day(s, day.date)]
        if not active_subjects:
            continue

        # 오늘 남은 시간 동안 과목을 순회하며 채우기
        idx = 0
        guard = 0
        while day.remaining_hours > 1e-6 and guard < 10_000:
            guard += 1
            s = active_subjects[idx % len(active_subjects)]
            idx += 1

            if remaining.get(s.name, 0.0) <= 1e-6:
                # 이 과목의 목표가 이미 채워졌으면 skip
                continue

            # 블록 크기 결정: min~max 사이에서, 남은 시간/남은 목표를 고려
            block = min(config.max_block_hours, day.remaining_hours, remaining[s.name])
            if block < config.min_block_hours:
                # 남은 시간이 너무 적어 최소 블록을 만들 수 없으면 종료
                break

            day.blocks.append(StudyBlock(subject_name=s.name, hours=float(block)))
            remaining[s.name] -= float(block)

    return days
