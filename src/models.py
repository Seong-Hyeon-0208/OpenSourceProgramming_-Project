
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
class UserConfig:
    """Scheduler configuration."""
    subjects: List[Subject]
    daily_available_hours: Dict[int, float]  # weekday (0=Mon..6=Sun) -> hours
    planning_horizon_days: int = 7

    # 학습 유형에 따라 UI에서 자동 설정됨
    min_block_hours: float = 1.0
    max_block_hours: float = 2.0


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
