from dataclasses import dataclass, field
from datetime import date
from typing import List


@dataclass
class Subject:
    """과목 정보"""
    name: str
    weekly_target_hours: float
    exam_date: date | None = None


@dataclass
class TimeBlock:
    """
    주간 시간표 블록

    weekday: 0=월 ... 6=일
    start_min/end_min: 00:00 기준 분 단위 (0~1440)
    label: "점심", "데이터통신 강의", "선형대수학" 등
    kind: "busy"(공부불가) 또는 "study"(공부)
    """
    weekday: int
    start_min: int
    end_min: int
    label: str
    kind: str = "busy"


@dataclass
class UserConfig:
    subjects: List[Subject]

    # 기간(일)
    planning_horizon_days: int = 7

    # 학습 유형에 따라 설정 (분배형 1~2, 몰입형 2~3)
    min_block_hours: float = 1.0
    max_block_hours: float = 2.0

    # 시간표 표시 범위
    day_start_hour: int = 9
    day_end_hour: int = 24

    # 슬롯 크기(분): 30 또는 60 추천
    slot_minutes: int = 30

    # 요일별 공부 불가능 블록
    busy_blocks: List[TimeBlock] = field(default_factory=list)
