from datetime import date, timedelta

from src.models import Subject, UserConfig
from src.scheduler import generate_weekly_grid_schedule


def test_exam_date_exclusion():
    today = date.today()
    subj = Subject(name="A", weekly_target_hours=10.0, exam_date=today)

    # 너희 최신 UserConfig는 daily_available_hours가 아니라
    # busy_blocks + day_start/end + slot 기반이므로 거기에 맞춰 구성
    cfg = UserConfig(
        subjects=[subj],
        planning_horizon_days=3,
        min_block_hours=1.0,
        max_block_hours=2.0,
        day_start_hour=9,
        day_end_hour=12,     # 하루 3시간만 열어두기
        slot_minutes=60,     # 1시간 슬롯
        busy_blocks=[],
    )

    # exam day 이후(다음날)부터 시작 → 과목이 스케줄에 들어가면 안 됨
    blocks = generate_weekly_grid_schedule(cfg, start_date=today + timedelta(days=1))

    # study 블록이 하나도 없어야 함 (busy는 있을 수 있으니 study만 검사)
    study_blocks = [b for b in blocks if b.kind == "study"]
    assert len(study_blocks) == 0

