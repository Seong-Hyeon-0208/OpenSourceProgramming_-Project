from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from models import Subject, TimeBlock, UserConfig


def _to_min(h: int, m: int) -> int:
    return h * 60 + m


def _hours_to_min(hours: float) -> int:
    return int(round(hours * 60))


def _need_minutes(subject: Subject, horizon_days: int) -> int:
    """
    단순 모델:
      horizon_days 동안 필요한 공부량(분) = (주당 목표/7) * horizon_days
    """
    need_hours = (subject.weekly_target_hours / 7.0) * horizon_days
    return _hours_to_min(need_hours)


def _active_on_date(subject: Subject, d: date) -> bool:
    """
    시험 다음날부터 제외 (시험일 당일은 포함).
    시험일 당일도 제외하고 싶으면: return d < subject.exam_date 로 바꾸면 됨.
    """
    if subject.exam_date is None:
        return True
    return d <= subject.exam_date


def _weekday_has_any_active_date(subject: Subject, start_date: date, horizon_days: int, weekday: int) -> bool:
    """
    주간 패턴(요일 기반) 시간표를 만들기 때문에,
    '기간 안에 이 요일이 단 하루라도 시험 전(또는 시험일)인 날이 있는가'를 확인.
    전부 시험 이후면 해당 요일에서는 그 과목 배정 X
    """
    for i in range(horizon_days):
        d = start_date + timedelta(days=i)
        if d.weekday() == weekday and _active_on_date(subject, d):
            return True
    return False


def generate_weekly_grid_schedule(cfg: UserConfig, start_date: date | None = None) -> List[TimeBlock]:
    """
    반환: busy + study TimeBlock 리스트
    - 가로: 요일
    - 세로: 시간 슬롯
    """
    if start_date is None:
        start_date = date.today()

    slot = int(cfg.slot_minutes)
    day_start = _to_min(int(cfg.day_start_hour), 0)
    day_end = _to_min(int(cfg.day_end_hour), 0)

    # 1) busy 슬롯 마킹
    busy_slots: Dict[int, set[int]] = {w: set() for w in range(7)}
    for b in cfg.busy_blocks:
        for t in range(b.start_min, b.end_min, slot):
            busy_slots[b.weekday].add(t)

    # 2) 남은 공부량(분)
    remaining: Dict[str, int] = {s.name: _need_minutes(s, cfg.planning_horizon_days) for s in cfg.subjects}

    # 3) 블록 길이(분)
    min_block = _hours_to_min(cfg.min_block_hours)
    max_block = _hours_to_min(cfg.max_block_hours)

    # 결과에는 busy도 포함
    result: List[TimeBlock] = list(cfg.busy_blocks)

    # 기간 내 등장하는 요일만 대상으로
    days = [start_date + timedelta(days=i) for i in range(cfg.planning_horizon_days)]
    weekdays_in_range = sorted(set(d.weekday() for d in days))

    # 4) 라운드로빈 채우기
    subj_idx = 0

    for w in weekdays_in_range:
        t = day_start
        guard = 0

        while t + slot <= day_end and guard < 100000:
            guard += 1

            if t in busy_slots[w]:
                t += slot
                continue

            # 남은 공부량이 있고, 기간 내 이 요일에 '활성 날짜'가 있는 과목만
            active_subjects: List[Subject] = []
            for s in cfg.subjects:
                if remaining.get(s.name, 0) <= 0:
                    continue
                if not _weekday_has_any_active_date(s, start_date, cfg.planning_horizon_days, w):
                    continue
                active_subjects.append(s)

            if not active_subjects:
                break

            s = active_subjects[subj_idx % len(active_subjects)]
            subj_idx += 1

            # 연속 빈 슬롯 길이(run) 계산
            run = 0
            tt = t
            while tt + slot <= day_end and tt not in busy_slots[w]:
                run += slot
                tt += slot

            block_len = min(max_block, run, remaining[s.name])

            # 최소 블록보다 작으면 패스
            if block_len < min_block:
                t += slot
                continue

            # 슬롯 점유 처리
            for tt in range(t, t + block_len, slot):
                busy_slots[w].add(tt)

            result.append(
                TimeBlock(
                    weekday=w,
                    start_min=t,
                    end_min=t + block_len,
                    label=s.name,
                    kind="study",
                )
            )

            remaining[s.name] -= block_len
            t += block_len

    return result
