
from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict


@dataclass
class Subject:
    """Represents a single subject or course to study."""
    name: str
    weekly_target_hours: float
    priority: int = 1  # 1~5 정도, 숫자가 클수록 중요
    exam_date: date | None = None


@dataclass
class UserConfig:
    """
    Global configuration for the scheduler.

    - subjects: 공부 과목 목록
    - daily_available_hours: 요일별 가용 시간 (0=월, 6=일)
    """
    subjects: List[Subject]
    daily_available_hours: Dict[int, float]  # weekday index -> hours

    planning_horizon_days: int = 7  # 며칠치 일정을 짤지
    max_block_hours: float = 2.0  # 한 번에 배정할 최대 공부 시간


@dataclass
class StudyBlock:
    """A single continuous block of study time for a subject."""
    subject_name: str
    hours: float


@dataclass
class ScheduleDay:
    """Schedule for a single day."""
    date: date
    total_available_hours: float
    blocks: List[StudyBlock] = field(default_factory=list)

    @property
    def used_hours(self) -> float:
        return sum(block.hours for block in self.blocks)

    @property
    def remaining_hours(self) -> float:
        return max(self.total_available_hours - self.used_hours, 0.0)
