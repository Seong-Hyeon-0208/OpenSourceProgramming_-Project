from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

from models import UserConfig, TimeBlock, Subject


def _to_min(h: int, m: int) -> int:
    return h * 60 + m


def _hours_to_min(hours: float) -> int:
    return int(round(hours * 60))


def _min_to_hhmm(t: int) -> str:
    return f"{t // 60:02d}:{t % 60:02d}"


def _is_subject_active(subject: Subject, d: date) -> bool:
    """
    시험 이후 그 과목 제외.
    - 시험일 당일은 포함, 다음날부터 제외 (요청 조건의 '시험 이후' 해석)
    """
    if subject.exam_date is None:
        return True
    return d <= subject.exam_date


def _build_busy_slots(cfg: UserConfig) -> Dict[int, set]:
    """weekday -> set(slot_start_min)"""
    slot = cfg.slot_minutes
    busy_slots = {w: set() for w in range(7)}
    for b in cfg.busy_blocks:
        start = max(0, min(1440, int(b.start_min)))
        end = max(0, min(1440, int(b.end_min)))
        if end <= start:
            continue
        for t in range(start, end, slot):
            busy_slots[b.weekday].add(t)
    return busy_slots


def generate_weekly_grid_schedule(
    cfg: UserConfig,
    start_date: date | None = None,
) -> List[TimeBlock]:
    """
    '가로=요일, 세로=시간' 시간표를 만들기 위한 스케줄러.

    반환: busy + study 블록을 합친 List[TimeBlock]
    - busy 블록은 cfg.busy_blocks 그대로 포함
    - study 블록은 빈 슬롯에 배정됨

    주의:
    - 이 함수는 "기간 N일"을 입력받지만, 결과는 '주간 패턴(weekday grid)' 형태로 생성됨.
    - 시험일 제외는 "기간 내 날짜들"을 기반으로 '활성 과목' 여부를 판단하여 반영.
    """
    if start_date is None:
        start_date = date.today()

    # 기간 안에 포함되는 요일(weekday)들만 대상으로 시간표 생성
    days = [start_date + timedelta(days=i) for i in range(cfg.planning_horizon_days)]
    weekdays_in_range = sorted(set(d.weekday() for d in days))

    # 과목별 필요한 총 공부 시간(분) - 단순 모델: 주당 목표를 기간에 비례해서 환산
    remaining_min: Dict[str, int] = {}
    for s in cfg.subjects:
        need_hours = (s.weekly_target_hours / 7.0) * cfg.planning_horizon_days
        remaining_min[s.name] = max(0, _hours_to_min(need_hours))

    slot = cfg.slot_minutes
    day_start = _to_min(cfg.day_start_hour, 0)
    day_end = _to_min(cfg.day_end_hour, 0)

    min_block = _hours_to_min(cfg.min_block_hours)
    max_block = _hours_to_min(cfg.max_block_hours)

    busy_slots = _build_busy_slots(cfg)

    # 결과는 busy + study
    result: List[TimeBlock] = [*cfg.busy_blocks]

    # 활성 과목 계산(기간 내 날짜 중 하루라도 '시험 이후'면 그 날짜에서는 제외되어야 함)
    # 주간 패턴이라 완전정확한 "날짜별 제외"는 어렵지만,
    # 최소한 "기간 내에서 시험이 지나버린 과목"은 배정이 줄어들도록 설계.
    def is_active_for_weekday(subject: Subject, weekday: int) -> bool:
        # 기간 내 '해당 weekday'인 날짜들 중 하나라도 과목이 활성인 날이 있으면 True
        for d in days:
            if d.weekday() == weekday and _is_subject_active(subject, d):
                return True
        return False

    subject_list = cfg.subjects[:]
    subj_idx = 0

    for w in weekdays_in_range:
        # 오늘(weekday)에 활성인 과목만
        active_subjects = [s for s in subject_list if is_active_for_weekday(s, w)]
        if not active_subjects:
            continue

        t = day_start
        guard = 0
        while t + slot <= day_end and guard < 20000:
            guard += 1

            if t in busy_slots[w]:
                t += slot
                continue

            # 남은 시간이 있는 과목만
            candidates = [s for s in active_subjects if remaining_min.get(s.name, 0) > 0]
            if not candidates:
                break

            s = candidates[subj_idx % len(candidates)]
            subj_idx += 1

            # 연속으로 비어있는 슬롯 길이(run) 계산
            run = 0
            tt = t
            while tt + slot <= day_end and (tt not in busy_slots[w]):
                run += slot
                tt += slot

            block_len = min(max_block, run, remaining_min[s.name])

            # 최소 블록보다 작으면 한 슬롯 이동
            if block_len < min_block:
                t += slot
                continue

            # 슬롯 마킹(공부가 차지)
            for k in range(t, t + block_len, slot):
                busy_slots[w].add(k)

            result.append(
                TimeBlock(
                    weekday=w,
                    start_min=t,
                    end_min=t + block_len,
                    label=s.name,
                    kind="study",
                )
            )

            remaining_min[s.name] -= block_len
            t += block_len

    return result
