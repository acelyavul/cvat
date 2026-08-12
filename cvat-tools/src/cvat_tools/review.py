import json
import shutil
from pathlib import Path

from .drawing import render_frame
from .frames import save_frame
from .policy import get_policy_path


def _enum_value(value):
    return getattr(value, "value", value)


def build_frame_review(client, task_id: int, frame: int):
    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()
    labels = {label.id: label for label in task.get_labels()}

    out = Path(f"output/review/task_{task_id}_frame_{frame}")
    out.mkdir(parents=True, exist_ok=True)

    original_path = out / "original.jpg"
    annotated_path = out / "annotated.jpg"

    save_frame(
        client,
        task_id,
        frame,
        str(original_path),
        quality="original",
    )

    render_frame(
        client,
        task_id,
        frame,
        str(annotated_path),
        show_ids=True,
    )

    items = []

    for shape in getattr(annotations, "shapes", []) or []:
        if getattr(shape, "frame", None) != frame:
            continue

        label = labels.get(getattr(shape, "label_id", None))

        specs = {
            attr.id: attr
            for attr in (getattr(label, "attributes", []) or [])
        } if label else {}

        attrs = {}

        for attr in getattr(shape, "attributes", []) or []:
            spec_id = getattr(attr, "spec_id", None)
            spec = specs.get(spec_id)

            name = (
                getattr(spec, "name", None)
                or f"spec_{spec_id}"
            )

            attrs[name] = getattr(attr, "value", None)

        items.append({
            "id": getattr(shape, "id", None),
            "frame": getattr(shape, "frame", None),
            "label": getattr(label, "name", None),
            "label_id": getattr(shape, "label_id", None),
            "type": _enum_value(getattr(shape, "type", None)),
            "points": list(getattr(shape, "points", []) or []),
            "attributes": attrs,
            "occluded": getattr(shape, "occluded", False),
            "outside": getattr(shape, "outside", False),
            "rotation": getattr(shape, "rotation", 0),
            "source": getattr(shape, "source", None),
        })

    metadata = {
        "task_id": task_id,
        "task_name": getattr(task, "name", None),
        "frame": frame,
        "annotation_count": len(items),
        "annotations": items,
    }

    metadata_path = out / "annotations.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    policy_source = get_policy_path()
    policy_path = out / "ANNOTATION_POLICY.md"

    if policy_source.exists():
        shutil.copyfile(policy_source, policy_path)
    else:
        policy_path.write_text(
            "# Missing annotation policy\n",
            encoding="utf-8",
        )

    return {
        "directory": out,
        "original": original_path,
        "annotated": annotated_path,
        "metadata": metadata_path,
        "policy": policy_path,
        "count": len(items),
    }


def build_task_review(client, task_id: int):
    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()
    labels = {label.id: label for label in task.get_labels()}

    out = Path(f"output/review/task_{task_id}")
    out.mkdir(parents=True, exist_ok=True)

    frames = {}

    for shape in getattr(annotations, "shapes", []) or []:
        frame = int(getattr(shape, "frame", 0))
        label = labels.get(getattr(shape, "label_id", None))

        specs = {
            attr.id: attr
            for attr in (getattr(label, "attributes", []) or [])
        } if label else {}

        attrs = {}

        for attr in getattr(shape, "attributes", []) or []:
            spec = specs.get(getattr(attr, "spec_id", None))
            name = (
                getattr(spec, "name", None)
                or f"spec_{getattr(attr, 'spec_id', '?')}"
            )
            attrs[name] = getattr(attr, "value", None)

        frames.setdefault(frame, []).append({
            "id": getattr(shape, "id", None),
            "label": getattr(label, "name", None),
            "label_id": getattr(shape, "label_id", None),
            "type": _enum_value(getattr(shape, "type", None)),
            "points": list(getattr(shape, "points", []) or []),
            "attributes": attrs,
        })

    track_count = len(
        list(getattr(annotations, "tracks", []) or [])
    )

    manifest = {
        "task_id": task_id,
        "task_name": getattr(task, "name", None),
        "frame_count": getattr(task, "size", None),
        "annotated_frame_count": len(frames),
        "shape_count": sum(len(v) for v in frames.values()),
        "track_count": track_count,
        "track_warning": (
            "Tracks exist. Task annotation retrieval contains track "
            "keyframes, not interpolated shapes."
            if track_count
            else None
        ),
        "frames": {
            str(frame): {
                "annotation_count": len(items),
                "annotation_ids": [
                    item["id"] for item in items
                ],
                "annotations": items,
            }
            for frame, items in sorted(frames.items())
        },
    }

    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    policy_source = get_policy_path()
    if policy_source.exists():
        shutil.copyfile(
            policy_source,
            out / "ANNOTATION_POLICY.md",
        )

    return {
        "directory": out,
        "manifest": manifest_path,
        "annotated_frames": len(frames),
        "shapes": manifest["shape_count"],
        "tracks": track_count,
    }


def build_annotation_review(
    client,
    task_id: int,
    annotation_id: int,
    padding_ratio: float = 0.25,
):
    from PIL import ImageDraw

    from .frames import get_frame_image

    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()

    shape = next(
        (
            item
            for item in (getattr(annotations, "shapes", []) or [])
            if getattr(item, "id", None) == annotation_id
        ),
        None,
    )

    if shape is None:
        raise ValueError(
            f"Annotation {annotation_id} not found in task {task_id}"
        )

    shape_type = _enum_value(getattr(shape, "type", None))

    if shape_type != "rectangle":
        raise ValueError(
            f"Annotation {annotation_id} is {shape_type}, not rectangle"
        )

    points = list(getattr(shape, "points", []) or [])

    if len(points) != 4:
        raise ValueError("Rectangle must have 4 coordinates")

    frame = int(shape.frame)

    image = get_frame_image(
        client,
        task_id,
        frame,
        quality="original",
    ).convert("RGB")

    x1, y1, x2, y2 = map(float, points)

    pad_x = max(40, (x2 - x1) * padding_ratio)
    pad_y = max(40, (y2 - y1) * padding_ratio)

    cx1 = max(0, int(x1 - pad_x))
    cy1 = max(0, int(y1 - pad_y))
    cx2 = min(image.width, int(x2 + pad_x))
    cy2 = min(image.height, int(y2 + pad_y))

    crop = image.crop((cx1, cy1, cx2, cy2))
    boxed = crop.copy()

    draw = ImageDraw.Draw(boxed)
    draw.rectangle(
        (
            x1 - cx1,
            y1 - cy1,
            x2 - cx1,
            y2 - cy1,
        ),
        outline="red",
        width=5,
    )

    labels = {
        label.id: label
        for label in task.get_labels()
    }

    label = labels.get(shape.label_id)

    specs = {
        attr.id: attr
        for attr in (getattr(label, "attributes", []) or [])
    } if label else {}

    attributes = {}

    for attr in getattr(shape, "attributes", []) or []:
        spec_id = getattr(attr, "spec_id", None)
        spec = specs.get(spec_id)

        name = (
            getattr(spec, "name", None)
            or f"spec_{spec_id}"
        )

        attributes[name] = getattr(attr, "value", None)

    out = Path(
        f"output/review/task_{task_id}/annotation_{annotation_id}"
    )
    out.mkdir(parents=True, exist_ok=True)

    crop_path = out / "crop.jpg"
    boxed_path = out / "boxed.jpg"
    metadata_path = out / "annotation.json"

    crop.save(crop_path, quality=95)
    boxed.save(boxed_path, quality=95)

    metadata = {
        "task_id": task_id,
        "annotation_id": annotation_id,
        "frame": frame,
        "label": getattr(label, "name", None),
        "label_id": shape.label_id,
        "type": shape_type,
        "points": points,
        "attributes": attributes,
        "frame_size": {
            "width": image.width,
            "height": image.height,
        },
        "crop_region": [cx1, cy1, cx2, cy2],
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    policy_source = get_policy_path()

    if policy_source.exists():
        shutil.copyfile(
            policy_source,
            out / "ANNOTATION_POLICY.md",
        )

    return {
        "directory": out,
        "crop": crop_path,
        "boxed": boxed_path,
        "metadata": metadata_path,
        "frame": frame,
        "label": getattr(label, "name", None),
        "attributes": attributes,
    }


def build_next_review_context(client, task_id: int):
    from .policy import policy_info
    from .progress import build_review_progress

    _, progress = build_review_progress(
        client,
        task_id,
        limit=1,
    )

    if progress["complete"]:
        return None

    frame = progress["next_frames"][0]

    packet = build_frame_review(
        client,
        task_id,
        frame,
    )

    metadata_path = Path(packet["metadata"])

    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    policy = policy_info()

    context = {
        "task_id": task_id,
        "frame": frame,
        "policy": {
            "path": policy["path"],
            "sha256": policy["sha256"],
        },
        "annotation_count": metadata["annotation_count"],
        "has_annotations": metadata["annotation_count"] > 0,
        "annotations": metadata["annotations"],
        "artifacts": {
            "original": str(packet["original"]),
            "annotated": str(packet["annotated"]),
            "metadata": str(packet["metadata"]),
            "policy": str(packet["policy"]),
        },
        "decision": {
            "allowed_statuses": [
                "PASS",
                "REVIEW",
                "FAIL",
            ],
            "allowed_actions": [
                "none",
                "inspect",
                "update",
                "delete",
                "add",
            ],
        },
        "instructions": [
            "Read the annotation policy.",
            "Inspect the original image.",
            "Inspect the annotated image.",
            "Compare every visible target object with current annotations.",
            "Check bbox geometry and attributes.",
            "Look for missing annotations.",
            "Record PASS, REVIEW, or FAIL.",
            "Do not modify CVAT unless explicitly authorized.",
        ],
    }

    context_path = Path(packet["directory"]) / "context.json"

    context_path.write_text(
        json.dumps(
            context,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "frame": frame,
        "annotation_count": metadata["annotation_count"],
        "directory": packet["directory"],
        "context": context_path,
        "original": packet["original"],
        "annotated": packet["annotated"],
        "policy_sha256": policy["sha256"],
    }
