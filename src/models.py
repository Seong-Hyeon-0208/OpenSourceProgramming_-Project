from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict


@dataclass
class Subject:
    """A course/subject to study."""
    name: str
    weekly_target_hours: float
    exam_date: date | None = None


@dataclass
class TimeBlock:
    """
    A time block in weekly grid.
    weekday: 0=Mon .. 6=Sun
    start_min/end_min: minutes from 00:00 (0~1440)
    kind: "busy" or "study"
    """
    weekday: int
    start_min: int
    end_min: int
    label: str
    kind: str = "busy"


@dataclass
class UserConfig:
    """Scheduler configuration."""
    subjects: List[Subject]

    # 스케줄 기간(일)
    planning_horizon_days: int = 7

    # 학습 유형(분배형/몰입형)에 의해 설정됨
    min_block_hours: float = 1.0
    max_block_hours: float = 2.0

    # 시간표 범위 및 슬롯 크기
    day_start_hour: int = 9
    day_end_hour: int = 24
    slot_minutes: int = 30

    # 공부 불가 시간(강의/식사 등)
    busy_blocks: List[TimeBlock] = field(default_factory=list)


@dataclass
class StudyBlock:
    subject_name: str
    hours: float


@dataclass
class ScheduleDay:
    date: date
    total_available_hours: float
    blocks: List[StudyBlock] = field(default_factory=list)

    @property
    def used_hours(self) -> float:
        return sum(b.hours for b in self.blocks)

    @property
    def remaining_hours(self) -> float:
        return max(self.total_available_hours - self.used_hours, 0.0)
