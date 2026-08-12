import hashlib
import json


def _enum_value(value):
    return getattr(value, "value", value)


def _attrs(item):
    values = []

    for attr in (getattr(item, "attributes", []) or []):
        values.append({
            "spec_id": getattr(attr, "spec_id", None),
            "value": str(getattr(attr, "value", "")),
        })

    return sorted(
        values,
        key=lambda x: (
            x["spec_id"] if x["spec_id"] is not None else -1,
            x["value"],
        ),
    )


def frame_annotation_state(annotations, frame: int):
    shapes = []

    for shape in (getattr(annotations, "shapes", []) or []):
        if getattr(shape, "frame", None) != frame:
            continue

        shapes.append({
            "id": getattr(shape, "id", None),
            "label_id": getattr(shape, "label_id", None),
            "type": _enum_value(getattr(shape, "type", None)),
            "points": list(getattr(shape, "points", []) or []),
            "attributes": _attrs(shape),
            "occluded": bool(getattr(shape, "occluded", False)),
            "outside": bool(getattr(shape, "outside", False)),
            "rotation": float(getattr(shape, "rotation", 0) or 0),
            "z_order": int(getattr(shape, "z_order", 0) or 0),
            "group": getattr(shape, "group", None),
        })

    tags = []

    for tag in (getattr(annotations, "tags", []) or []):
        if getattr(tag, "frame", None) != frame:
            continue

        tags.append({
            "id": getattr(tag, "id", None),
            "label_id": getattr(tag, "label_id", None),
            "attributes": _attrs(tag),
            "group": getattr(tag, "group", None),
        })

    shapes.sort(key=lambda x: (x["id"] is None, x["id"] or 0))
    tags.sort(key=lambda x: (x["id"] is None, x["id"] or 0))

    return {
        "frame": frame,
        "shapes": shapes,
        "tags": tags,
    }


def frame_annotation_sha256(annotations, frame: int):
    state = frame_annotation_state(
        annotations,
        frame,
    )

    encoded = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()
