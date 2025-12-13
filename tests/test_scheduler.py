
from datetime import date, timedelta

from models import Subject, UserConfig
from scheduler import generate_schedule
from src.models import Subject, UserConfig

def test_exam_date_exclusion():
    today = date.today()
    subj = Subject(name="A", weekly_target_hours=10.0, exam_date=today)
    cfg = UserConfig(
        subjects=[subj],
        daily_available_hours={i: 3.0 for i in range(7)},
        planning_horizon_days=3,
        min_block_hours=1.0,
        max_block_hours=2.0,
    )
    schedule = generate_schedule(cfg, start_date=today + timedelta(days=1))  # exam day 이후부터 시작
    # exam day 다음날부터는 제외되므로 blocks가 없어야 함
    assert all(len(d.blocks) == 0 for d in schedule)
