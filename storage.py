
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, Any, List

from .models import Subject, UserConfig


def _date_to_str(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _date_from_str(s: str | None) -> date | None:
    if s is None:
        return None
    return date.fromisoformat(s)


def config_to_dict(config: UserConfig) -> Dict[str, Any]:
    return {
        "subjects": [
            {
                "name": s.name,
                "weekly_target_hours": s.weekly_target_hours,
                "priority": s.priority,
                "exam_date": _date_to_str(s.exam_date),
            }
            for s in config.subjects
        ],
        "daily_available_hours": config.daily_available_hours,
        "planning_horizon_days": config.planning_horizon_days,
        "max_block_hours": config.max_block_hours,
    }


def config_from_dict(data: Dict[str, Any]) -> UserConfig:
    subjects: List[Subject] = [
        Subject(
            name=s["name"],
            weekly_target_hours=float(s["weekly_target_hours"]),
            priority=int(s.get("priority", 1)),
            exam_date=_date_from_str(s.get("exam_date")),
        )
        for s in data.get("subjects", [])
    ]
    return UserConfig(
        subjects=subjects,
        daily_available_hours={
            int(k): float(v) for k, v in data.get("daily_available_hours", {}).items()
        },
        planning_horizon_days=int(data.get("planning_horizon_days", 7)),
        max_block_hours=float(data.get("max_block_hours", 2.0)),
    )


def save_config(config: UserConfig, path: str | Path) -> None:
    path = Path(path)
    payload = config_to_dict(config)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config(path: str | Path) -> UserConfig:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return config_from_dict(data)
