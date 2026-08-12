from cvat_sdk.api_client.models import (
    AttributeValRequest,
    LabeledShapeRequest,
    PatchedLabeledDataRequest,
    ShapeType,
)
from rich.console import Console
from rich.table import Table

from .frames import get_frame_image

console = Console()


def _enum_value(value):
    return getattr(value, "value", value)


def _label_map(task):
    return {label.id: label.name for label in task.get_labels()}


def _label_specs(task):
    result = {}

    for label in task.get_labels():
        result[label.id] = {
            attr.id: attr
            for attr in (getattr(label, "attributes", []) or [])
        }

    return result


def _format_attributes(shape, specs):
    values = []

    for attr in getattr(shape, "attributes", []) or []:
        spec = specs.get(getattr(attr, "spec_id", None))
        name = getattr(spec, "name", f"spec:{getattr(attr, 'spec_id', '?')}")
        value = getattr(attr, "value", "?")
        values.append(f"{name}={value}")

    return ", ".join(values) if values else "-"


def list_annotations(client, task_id: int, frame: int | None = None):
    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()

    labels = _label_map(task)
    specs_by_label = _label_specs(task)

    shapes = list(getattr(annotations, "shapes", []) or [])
    tracks = list(getattr(annotations, "tracks", []) or [])
    tags = list(getattr(annotations, "tags", []) or [])

    if frame is not None:
        shapes = [
            shape
            for shape in shapes
            if getattr(shape, "frame", None) == frame
        ]

        tags = [
            tag
            for tag in tags
            if getattr(tag, "frame", None) == frame
        ]

    table = Table(title=f"Task {task_id} - Shapes")
    table.add_column("ID", justify="right")
    table.add_column("Frame", justify="right")
    table.add_column("Label")
    table.add_column("Type")
    table.add_column("Points")
    table.add_column("Attributes")
    table.add_column("Occluded")
    table.add_column("Outside")
    table.add_column("Rotation")
    table.add_column("Source")

    for shape in shapes:
        label_id = getattr(shape, "label_id", None)

        table.add_row(
            str(getattr(shape, "id", "-")),
            str(getattr(shape, "frame", "-")),
            f"{labels.get(label_id, '?')} ({label_id})",
            str(_enum_value(getattr(shape, "type", "-"))),
            str(getattr(shape, "points", None)),
            _format_attributes(
                shape,
                specs_by_label.get(label_id, {}),
            ),
            str(getattr(shape, "occluded", False)),
            str(getattr(shape, "outside", False)),
            str(getattr(shape, "rotation", 0)),
            str(getattr(shape, "source", "-")),
        )

    console.print(table)

    if tracks:
        track_table = Table(title=f"Task {task_id} - Tracks")
        track_table.add_column("Track ID", justify="right")
        track_table.add_column("Label")
        track_table.add_column("Start", justify="right")
        track_table.add_column("Keyframes", justify="right")
        track_table.add_column("Source")

        visible_tracks = 0

        for track in tracks:
            track_shapes = list(getattr(track, "shapes", []) or [])

            if frame is not None:
                matching = [
                    shape
                    for shape in track_shapes
                    if getattr(shape, "frame", None) == frame
                ]

                if not matching:
                    continue

            visible_tracks += 1

            label_id = getattr(track, "label_id", None)

            track_table.add_row(
                str(getattr(track, "id", "-")),
                f"{labels.get(label_id, '?')} ({label_id})",
                str(getattr(track, "frame", "-")),
                str(len(track_shapes)),
                str(getattr(track, "source", "-")),
            )

        console.print(track_table)
    else:
        visible_tracks = 0

    console.print(
        f"[bold]Shapes:[/bold] {len(shapes)}   "
        f"[bold]Tracks:[/bold] {visible_tracks}   "
        f"[bold]Tags:[/bold] {len(tags)}"
    )


def _resolve_box_attributes(label, args: list[str]):
    specs = list(getattr(label, "attributes", []) or [])

    by_name = {
        spec.name: spec
        for spec in specs
    }

    # Start with explicit CVAT defaults.
    values = {
        spec.name: str(getattr(spec, "default_value", ""))
        for spec in specs
    }

    for raw in args:
        if "=" not in raw:
            raise ValueError(
                f"Invalid attribute '{raw}'. "
                "Expected NAME=VALUE."
            )

        name, value = raw.split("=", 1)
        name = name.strip()
        value = value.strip()

        if name not in by_name:
            available = ", ".join(sorted(by_name)) or "(none)"
            raise ValueError(
                f"Unknown attribute '{name}' for label '{label.name}'. "
                f"Available: {available}"
            )

        spec = by_name[name]
        input_type = _enum_value(
            getattr(spec, "input_type", "")
        )

        if input_type == "checkbox":
            normalized = value.lower()

            if normalized not in {"true", "false"}:
                raise ValueError(
                    f"{name} is a checkbox; use true or false."
                )

            value = normalized

        values[name] = value

    return [
        AttributeValRequest(
            spec_id=by_name[name].id,
            value=value,
        )
        for name, value in values.items()
    ]


def add_box(
    client,
    task_id: int,
    frame: int,
    label_name: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    attribute_args: list[str] | None = None,
):
    if x1 >= x2:
        raise ValueError("x1 must be smaller than x2")

    if y1 >= y2:
        raise ValueError("y1 must be smaller than y2")

    if x1 < 0 or y1 < 0:
        raise ValueError("coordinates cannot be negative")

    task = client.tasks.retrieve(task_id)

    labels = [
        label
        for label in task.get_labels()
        if label.name == label_name
    ]

    if not labels:
        raise ValueError(f"Label not found: {label_name}")

    if len(labels) > 1:
        raise ValueError(f"Ambiguous label: {label_name}")

    label = labels[0]

    if _enum_value(getattr(label, "type", None)) != "rectangle":
        raise ValueError(
            f"Label '{label.name}' is type "
            f"'{_enum_value(getattr(label, 'type', None))}', "
            "not rectangle."
        )

    image = get_frame_image(
        client,
        task_id,
        frame,
        quality="original",
    )

    if x2 > image.width or y2 > image.height:
        raise ValueError(
            f"Box exceeds frame dimensions "
            f"{image.width}x{image.height}"
        )

    attributes = _resolve_box_attributes(
        label,
        attribute_args or [],
    )

    before = task.get_annotations()

    before_ids = {
        shape.id
        for shape in (before.shapes or [])
        if shape.id is not None
    }

    request = PatchedLabeledDataRequest(
        shapes=[
            LabeledShapeRequest(
                type=ShapeType("rectangle"),
                label_id=label.id,
                frame=frame,
                points=[x1, y1, x2, y2],
                attributes=attributes,
                occluded=False,
                outside=False,
                rotation=0.0,
                source="manual",
            )
        ]
    )

    client.api_client.tasks_api.partial_update_annotations(
        "create",
        task_id,
        patched_labeled_data_request=request,
    )

    fresh_task = client.tasks.retrieve(task_id)
    after = fresh_task.get_annotations()

    created = [
        shape
        for shape in (after.shapes or [])
        if shape.id not in before_ids
        and shape.frame == frame
        and shape.label_id == label.id
        and _enum_value(shape.type) == "rectangle"
    ]

    if not created:
        raise RuntimeError(
            "CVAT accepted the request but the new annotation "
            "could not be verified."
        )

    shape = created[-1]

    specs = {
        attr.id: attr
        for attr in (getattr(label, "attributes", []) or [])
    }

    return {
        "id": shape.id,
        "frame": shape.frame,
        "label": label.name,
        "label_id": label.id,
        "points": list(shape.points),
        "attributes": _format_attributes(shape, specs),
    }


def _find_standalone_shape(task, annotation_id: int):
    annotations = task.get_annotations()

    for shape in (getattr(annotations, "shapes", []) or []):
        if getattr(shape, "id", None) == annotation_id:
            return shape

    for track in (getattr(annotations, "tracks", []) or []):
        if getattr(track, "id", None) == annotation_id:
            raise ValueError(
                f"ID {annotation_id} is a track, not a standalone shape. "
                "Track deletion is intentionally not handled here."
            )

    for tag in (getattr(annotations, "tags", []) or []):
        if getattr(tag, "id", None) == annotation_id:
            raise ValueError(
                f"ID {annotation_id} is a tag, not a standalone shape."
            )

    raise ValueError(f"Annotation ID {annotation_id} not found.")


def _shape_summary(task, shape):
    labels = _label_map(task)
    label_id = getattr(shape, "label_id", None)

    specs = {
        attr.id: attr
        for label in task.get_labels()
        if label.id == label_id
        for attr in (getattr(label, "attributes", []) or [])
    }

    return {
        "id": shape.id,
        "frame": shape.frame,
        "label": labels.get(label_id, "?"),
        "label_id": label_id,
        "type": _enum_value(shape.type),
        "points": list(getattr(shape, "points", []) or []),
        "attributes": _format_attributes(shape, specs),
    }


def delete_shape(
    client,
    task_id: int,
    annotation_id: int,
    yes: bool = False,
):
    task = client.tasks.retrieve(task_id)
    shape = _find_standalone_shape(task, annotation_id)

    summary = _shape_summary(task, shape)

    if not yes:
        return False, summary

    attributes = [
        AttributeValRequest(
            spec_id=attr.spec_id,
            value=attr.value,
        )
        for attr in (getattr(shape, "attributes", []) or [])
    ]

    request_shape = LabeledShapeRequest(
        id=shape.id,
        type=ShapeType(_enum_value(shape.type)),
        label_id=shape.label_id,
        frame=shape.frame,
        points=list(getattr(shape, "points", []) or []),
        attributes=attributes,
        occluded=bool(getattr(shape, "occluded", False)),
        outside=bool(getattr(shape, "outside", False)),
        rotation=float(getattr(shape, "rotation", 0.0) or 0.0),
        z_order=int(getattr(shape, "z_order", 0) or 0),
        source=str(getattr(shape, "source", "manual")),
    )

    client.api_client.tasks_api.partial_update_annotations(
        "delete",
        task_id,
        patched_labeled_data_request=PatchedLabeledDataRequest(
            shapes=[request_shape]
        ),
    )

    fresh_task = client.tasks.retrieve(task_id)
    fresh_annotations = fresh_task.get_annotations()

    still_exists = any(
        getattr(item, "id", None) == annotation_id
        for item in (getattr(fresh_annotations, "shapes", []) or [])
    )

    if still_exists:
        raise RuntimeError(
            f"Deletion verification failed: annotation "
            f"{annotation_id} still exists."
        )

    return True, summary


def _merge_shape_attributes(label, shape, attribute_args: list[str]):
    specs = list(getattr(label, "attributes", []) or [])

    by_name = {spec.name: spec for spec in specs}
    by_id = {spec.id: spec for spec in specs}

    values = {
        attr.spec_id: str(attr.value)
        for attr in (getattr(shape, "attributes", []) or [])
    }

    for raw in attribute_args:
        if "=" not in raw:
            raise ValueError(
                f"Invalid attribute '{raw}'. Expected NAME=VALUE."
            )

        name, value = raw.split("=", 1)
        name = name.strip()
        value = value.strip()

        spec = by_name.get(name)

        if spec is None:
            available = ", ".join(sorted(by_name)) or "(none)"
            raise ValueError(
                f"Unknown attribute '{name}' for label '{label.name}'. "
                f"Available: {available}"
            )

        input_type = _enum_value(
            getattr(spec, "input_type", None)
        )

        if input_type == "checkbox":
            value = value.lower()

            if value not in {"true", "false"}:
                raise ValueError(
                    f"{name} must be true or false."
                )

        values[spec.id] = value

    return [
        AttributeValRequest(
            spec_id=spec_id,
            value=value,
        )
        for spec_id, value in values.items()
        if spec_id in by_id
    ]


def update_shape(
    client,
    task_id: int,
    annotation_id: int,
    x1: float | None = None,
    y1: float | None = None,
    x2: float | None = None,
    y2: float | None = None,
    attribute_args: list[str] | None = None,
    yes: bool = False,
):
    attribute_args = attribute_args or []

    task = client.tasks.retrieve(task_id)
    shape = _find_standalone_shape(task, annotation_id)

    if _enum_value(getattr(shape, "type", None)) != "rectangle":
        raise ValueError(
            "This command currently updates standalone rectangles only."
        )

    labels = {
        label.id: label
        for label in task.get_labels()
    }

    label = labels.get(shape.label_id)

    if label is None:
        raise ValueError(
            f"Label {shape.label_id} not found."
        )

    coords = [x1, y1, x2, y2]
    supplied = [v is not None for v in coords]

    if any(supplied) and not all(supplied):
        raise ValueError(
            "To change geometry provide all of "
            "--x1 --y1 --x2 --y2."
        )

    if not any(supplied) and not attribute_args:
        raise ValueError("Nothing to update.")

    old_summary = _shape_summary(task, shape)

    if all(supplied):
        new_points = [
            float(x1),
            float(y1),
            float(x2),
            float(y2),
        ]

        nx1, ny1, nx2, ny2 = new_points

        if nx1 >= nx2 or ny1 >= ny2:
            raise ValueError("Invalid rectangle geometry.")

        if nx1 < 0 or ny1 < 0:
            raise ValueError("Coordinates cannot be negative.")

        image = get_frame_image(
            client,
            task_id,
            shape.frame,
            quality="original",
        )

        if nx2 > image.width or ny2 > image.height:
            raise ValueError(
                f"Box exceeds frame dimensions "
                f"{image.width}x{image.height}."
            )
    else:
        new_points = list(shape.points)

    new_attributes = _merge_shape_attributes(
        label,
        shape,
        attribute_args,
    )

    attr_preview = {
        spec.name: next(
            (
                attr.value
                for attr in new_attributes
                if attr.spec_id == spec.id
            ),
            None,
        )
        for spec in (getattr(label, "attributes", []) or [])
    }

    preview = {
        "id": shape.id,
        "frame": shape.frame,
        "label": label.name,
        "label_id": label.id,
        "type": "rectangle",
        "points": new_points,
        "attributes": ", ".join(
            f"{name}={value}"
            for name, value in attr_preview.items()
            if value is not None
        ) or "-",
    }

    if not yes:
        return False, old_summary, preview

    kwargs = {
        "id": shape.id,
        "type": ShapeType("rectangle"),
        "label_id": shape.label_id,
        "frame": shape.frame,
        "points": new_points,
        "attributes": new_attributes,
        "occluded": bool(getattr(shape, "occluded", False)),
        "outside": bool(getattr(shape, "outside", False)),
        "rotation": float(getattr(shape, "rotation", 0.0) or 0.0),
        "z_order": int(getattr(shape, "z_order", 0) or 0),
        "source": str(
            _enum_value(getattr(shape, "source", "manual"))
        ),
    }

    group = getattr(shape, "group", None)
    if group is not None:
        kwargs["group"] = group

    score = getattr(shape, "score", None)
    if score is not None:
        kwargs["score"] = score

    request_shape = LabeledShapeRequest(**kwargs)

    client.api_client.tasks_api.partial_update_annotations(
        "update",
        task_id,
        patched_labeled_data_request=PatchedLabeledDataRequest(
            shapes=[request_shape]
        ),
    )

    fresh_task = client.tasks.retrieve(task_id)
    updated = _find_standalone_shape(
        fresh_task,
        annotation_id,
    )

    new_summary = _shape_summary(
        fresh_task,
        updated,
    )

    return True, old_summary, new_summary


def _shape_to_request(shape):
    attributes = [
        AttributeValRequest(
            spec_id=attr.spec_id,
            value=attr.value,
        )
        for attr in (getattr(shape, "attributes", []) or [])
    ]

    kwargs = {
        "id": shape.id,
        "type": ShapeType(_enum_value(shape.type)),
        "label_id": shape.label_id,
        "frame": shape.frame,
        "points": list(getattr(shape, "points", []) or []),
        "attributes": attributes,
        "occluded": bool(getattr(shape, "occluded", False)),
        "outside": bool(getattr(shape, "outside", False)),
        "rotation": float(getattr(shape, "rotation", 0.0) or 0.0),
        "z_order": int(getattr(shape, "z_order", 0) or 0),
        "source": str(_enum_value(getattr(shape, "source", "manual"))),
    }

    group = getattr(shape, "group", None)
    if group is not None:
        kwargs["group"] = group

    return LabeledShapeRequest(**kwargs)


def bulk_delete_shapes(
    client,
    task_id: int,
    frame: int | None = None,
    label_name: str | None = None,
    shape_type: str | None = None,
    yes: bool = False,
):
    if frame is None and label_name is None and shape_type is None:
        raise ValueError(
            "At least one filter is required: frame, label or type."
        )

    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()

    labels = {
        label.id: label.name
        for label in task.get_labels()
    }

    matches = []

    for shape in (getattr(annotations, "shapes", []) or []):
        if frame is not None and shape.frame != frame:
            continue

        if label_name is not None and labels.get(shape.label_id) != label_name:
            continue

        if shape_type is not None and _enum_value(shape.type) != shape_type:
            continue

        matches.append(shape)

    summaries = [
        _shape_summary(task, shape)
        for shape in matches
    ]

    if not yes or not matches:
        return False, summaries

    ids = {shape.id for shape in matches}

    client.api_client.tasks_api.partial_update_annotations(
        "delete",
        task_id,
        patched_labeled_data_request=PatchedLabeledDataRequest(
            shapes=[
                _shape_to_request(shape)
                for shape in matches
            ]
        ),
    )

    fresh_task = client.tasks.retrieve(task_id)
    fresh = fresh_task.get_annotations()

    remaining = {
        shape.id
        for shape in (getattr(fresh, "shapes", []) or [])
        if shape.id in ids
    }

    if remaining:
        raise RuntimeError(
            f"Bulk deletion verification failed. "
            f"Still present: {sorted(remaining)}"
        )

    return True, summaries
