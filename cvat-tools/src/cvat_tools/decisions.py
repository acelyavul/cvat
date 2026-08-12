import json
from datetime import datetime, timezone
from pathlib import Path

from .policy import policy_info

VALID_STATUSES = {"PASS", "REVIEW", "FAIL"}
VALID_ACTIONS = {
    "none",
    "inspect",
    "update",
    "delete",
    "add",
}


def record_decision(
    task_id: int,
    frame: int,
    status: str,
    reason: str,
    action: str = "none",
    annotation_ids: list[int] | None = None,
    annotation_sha256: str | None = None,
):
    status = status.upper().strip()
    action = action.lower().strip()

    if status not in VALID_STATUSES:
        raise ValueError(
            f"status must be one of: {sorted(VALID_STATUSES)}"
        )

    if action not in VALID_ACTIONS:
        raise ValueError(
            f"action must be one of: {sorted(VALID_ACTIONS)}"
        )

    if not reason.strip():
        raise ValueError("reason cannot be empty")

    out = Path(f"output/review/task_{task_id}")
    out.mkdir(parents=True, exist_ok=True)

    path = out / "decisions.jsonl"

    policy = policy_info()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "frame": frame,
        "policy_sha256": policy["sha256"],
        "policy_path": policy["path"],
        "annotation_sha256": annotation_sha256,
        "status": status,
        "reason": reason.strip(),
        "recommended_action": action,
        "annotation_ids": annotation_ids or [],
    }

    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )

    return path, record


def load_decisions(task_id: int):
    path = Path(
        f"output/review/task_{task_id}/decisions.jsonl"
    )

    if not path.exists():
        return []

    records = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records
