
from datetime import date

from src.models import Subject, UserConfig
from src.scheduler import generate_initial_schedule


def test_total_hours_not_exceed_available():
    subjects = [
        Subject(name="Test", weekly_target_hours=7.0, priority=3, exam_date=date.today())
    ]
    daily_hours = {i: 2.0 for i in range(7)}
    cfg = UserConfig(subjects=subjects, daily_available_hours=daily_hours, planning_horizon_days=7, max_block_hours=2.0)
    schedule = generate_initial_schedule(cfg)

    for day in schedule:
        assert day.used_hours <= day.total_available_hours + 1e-6
