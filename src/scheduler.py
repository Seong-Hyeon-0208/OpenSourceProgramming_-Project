
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from models import UserConfig, ScheduleDay, StudyBlock, Subject

from models import UserConfig, TimeBlock, Subject
from datetime import date, timedelta

def _to_min(h: int, m: int) -> int:
    return h * 60 + m

def _hours_to_min(hours: float) -> int:
    return int(round(hours * 60))

def _is_subject_active(subject: Subject, d: date) -> bool:
    if subject.exam_date is None:
        return True
    return d <= subject.exam_date  # 시험 다음날부터 제외

def generate_weekly_grid_schedule(cfg: UserConfig, start_date: date | None = None):
    """
    반환:
      - busy + study 블록들을 합친 리스트[List[TimeBlock]]
    """
    if start_date is None:
        start_date = date.today()

    # 1) 스케줄 기간에 해당하는 날짜들의 weekday 목록(월~일)을 만든다
    days = [start_date + timedelta(days=i) for i in range(cfg.planning_horizon_days)]
    weekdays_in_range = sorted(set(d.weekday() for d in days))

    # 2) 과목별 필요한 총 공부 시간(분) (단순: 주당목표 * horizon/7)
    remaining_min = {}
    for s in cfg.subjects:
        need_hours = (s.weekly_target_hours / 7.0) * cfg.planning_horizon_days
        remaining_min[s.name] = _hours_to_min(need_hours)

    # 3) 요일별로 사용 가능한 슬롯 생성 (예: 09:00~24:00, 30분 단위)
    slot = cfg.slot_minutes
    day_start = _to_min(cfg.day_start_hour, 0)
    day_end = _to_min(cfg.day_end_hour, 0)

    # 요일별 busy map: weekday -> set(slot_start_min)
    busy_slots = {w: set() for w in range(7)}
    for b in cfg.busy_blocks:
        for t in range(b.start_min, b.end_min, slot):
            busy_slots[b.weekday].add(t)

    # 결과 블록은 busy + study를 함께 반환
    result_blocks = list(cfg.busy_blocks)

    # 4) 공부 블록 길이(분) 설정: 몰입형/분배형
    min_block = _hours_to_min(cfg.min_block_hours)
    max_block = _hours_to_min(cfg.max_block_hours)

    # 5) 빈 슬롯에 과목을 채우기(라운드로빈)
    subject_list = cfg.subjects[:]
    subj_idx = 0

    for w in weekdays_in_range:
        t = day_start
        while t + slot <= day_end:
            # busy면 skip
            if t in busy_slots[w]:
                t += slot
                continue

            # 남은 과목이 없으면 종료
            active_subjects = [s for s in subject_list if remaining_min.get(s.name, 0) > 0]
            if not active_subjects:
                break

            # 현재 과목 선택(라운드로빈)
            s = active_subjects[subj_idx % len(active_subjects)]
            subj_idx += 1

            # 시험 이후는 제외(기간 내 날짜들 중 같은 weekday가 여러개일 수 있으니,
            # "start_date 기준 첫 주"처럼 단순화할 경우엔 시험 제외가 약해질 수 있음.
            # 최소 구현에서는 weekday 기준 스케줄만 만들고,
            # 시험 제외는 '기간 안에 시험이 지난 경우 그 요일 전체 제외'로 확장 가능.
            # 여기서는 간단히: 시험이 start_date 기준 7일 안이면 반영 정도로만.
            # (정교화는 다음 단계에서)
            # ----

            # 블록을 만들 수 있는 최대 길이 계산 (연속 빈 슬롯 이어붙이기)
            run = 0
            tt = t
            while tt + slot <= day_end and tt not in busy_slots[w]:
                run += slot
                tt += slot
            # 실제 배치할 길이
            block_len = min(max_block, run, remaining_min[s.name])
            if block_len < min_block:
                t += slot
                continue

            # 해당 구간 슬롯들을 busy로 마킹 (공부가 차지)
            for tt in range(t, t + block_len, slot):
                busy_slots[w].add(tt)

            result_blocks.append(TimeBlock(
                weekday=w,
                start_min=t,
                end_min=t + block_len,
                label=s.name,
                kind="study"
            ))
            remaining_min[s.name] -= block_len

            t += block_len

    return result_blocks

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
