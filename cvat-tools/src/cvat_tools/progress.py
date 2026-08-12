import json
from pathlib import Path

from .decisions import load_decisions
from .policy import policy_info
from .state import frame_annotation_sha256


def build_review_progress(
    client,
    task_id: int,
    limit: int = 20,
):
    if limit < 1:
        raise ValueError("limit must be >= 1")

    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()

    task_size = int(getattr(task, "size", 0) or 0)
    all_frames = set(range(task_size))

    shapes = list(getattr(annotations, "shapes", []) or [])
    tracks = list(getattr(annotations, "tracks", []) or [])

    annotated_frames = {
        int(shape.frame)
        for shape in shapes
        if getattr(shape, "frame", None) is not None
    }

    decisions = load_decisions(task_id)
    current_policy = policy_info()
    current_sha = current_policy["sha256"]

    # decisions.jsonl append-only olduğu için aynı frame için
    # en son kayıt geçerli kabul edilir.
    latest_by_frame = {}

    for record in decisions:
        frame = record.get("frame")

        if frame is None:
            continue

        latest_by_frame[int(frame)] = record

    current_decisions = {}
    stale_frames = []
    stale_policy_frames = []
    stale_annotation_frames = []

    for frame, record in latest_by_frame.items():
        policy_matches = (
            record.get("policy_sha256") == current_sha
        )

        current_annotation_sha = frame_annotation_sha256(
            annotations,
            frame,
        )

        annotation_matches = (
            record.get("annotation_sha256")
            == current_annotation_sha
        )

        if policy_matches and annotation_matches:
            current_decisions[frame] = record
            continue

        stale_frames.append(frame)

        if not policy_matches:
            stale_policy_frames.append(frame)

        if not annotation_matches:
            stale_annotation_frames.append(frame)

    counts = {
        "PASS": 0,
        "REVIEW": 0,
        "FAIL": 0,
    }

    for record in current_decisions.values():
        status = record.get("status")

        if status in counts:
            counts[status] += 1

    reviewed_current = set(current_decisions)

    pending_frames = sorted(
        all_frames - reviewed_current
    )

    # Öncelik:
    # 1. policy değiştiği için stale olanlar
    # 2. hiç/current policy ile review edilmemiş olanlar
    ordered_pending = []

    for frame in sorted(set(stale_frames)):
        if frame in all_frames:
            ordered_pending.append(frame)

    for frame in pending_frames:
        if frame not in ordered_pending:
            ordered_pending.append(frame)

    progress = {
        "task_id": task_id,
        "task_name": getattr(task, "name", None),
        "frame_count": task_size,
        "shape_count": len(shapes),
        "track_count": len(tracks),
        "annotated_frame_count": len(annotated_frames),
        "policy": current_policy,
        "decision_record_count": len(decisions),
        "latest_decision_count": len(latest_by_frame),
        "current_policy_decision_count": len(current_decisions),
        "status_counts": counts,
        "stale_policy_frames": sorted(set(stale_policy_frames)),
        "stale_annotation_frames": sorted(set(stale_annotation_frames)),
        "pending_count": len(ordered_pending),
        "next_frames": ordered_pending[:limit],
        "complete": len(ordered_pending) == 0,
    }

    out = Path(f"output/review/task_{task_id}")
    out.mkdir(parents=True, exist_ok=True)

    path = out / "progress.json"

    path.write_text(
        json.dumps(
            progress,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return path, progress
