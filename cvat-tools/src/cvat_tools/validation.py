from rich.console import Console
from rich.table import Table

console = Console()


def _enum_value(value):
    return getattr(value, "value", value)


def validate_task_annotations(client, task_id: int, frame: int | None = None):
    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()

    meta, _ = client.api_client.tasks_api.retrieve_data_meta(task_id)
    frames_meta = list(getattr(meta, "frames", []) or [])

    labels = {
        label.id: label
        for label in task.get_labels()
    }

    issues = []

    shapes = list(getattr(annotations, "shapes", []) or [])

    if frame is not None:
        shapes = [
            shape
            for shape in shapes
            if getattr(shape, "frame", None) == frame
        ]

    for shape in shapes:
        shape_id = getattr(shape, "id", None)
        frame_id = getattr(shape, "frame", None)
        label_id = getattr(shape, "label_id", None)
        shape_type = _enum_value(getattr(shape, "type", None))
        points = list(getattr(shape, "points", []) or [])

        label = labels.get(label_id)

        if label is None:
            issues.append(
                (
                    shape_id,
                    frame_id,
                    "ERROR",
                    f"Unknown label_id={label_id}",
                )
            )
            continue

        label_type = _enum_value(getattr(label, "type", None))

        if label_type not in (None, "any") and shape_type != label_type:
            issues.append(
                (
                    shape_id,
                    frame_id,
                    "ERROR",
                    f"Shape type={shape_type} but label type={label_type}",
                )
            )

        if frame_id is None or frame_id < 0 or frame_id >= len(frames_meta):
            issues.append(
                (
                    shape_id,
                    frame_id,
                    "ERROR",
                    f"Invalid frame index: {frame_id}",
                )
            )
            continue

        frame_meta = frames_meta[frame_id]
        width = getattr(frame_meta, "width", None)
        height = getattr(frame_meta, "height", None)

        if shape_type == "rectangle":
            if len(points) != 4:
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"Rectangle must have 4 points, got {len(points)}",
                    )
                )
                continue

            x1, y1, x2, y2 = points

            if x1 >= x2 or y1 >= y2:
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"Invalid rectangle geometry: {points}",
                    )
                )

            if min(x1, y1, x2, y2) < 0:
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"Negative rectangle coordinates: {points}",
                    )
                )

            if width is not None and (x1 > width or x2 > width):
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"X coordinate outside frame width={width}: {points}",
                    )
                )

            if height is not None and (y1 > height or y2 > height):
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"Y coordinate outside frame height={height}: {points}",
                    )
                )

        specs = {
            attr.id: attr
            for attr in (getattr(label, "attributes", []) or [])
        }

        seen_specs = set()

        for attr in getattr(shape, "attributes", []) or []:
            spec_id = getattr(attr, "spec_id", None)
            value = str(getattr(attr, "value", ""))

            if spec_id in seen_specs:
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"Duplicate attribute spec_id={spec_id}",
                    )
                )

            seen_specs.add(spec_id)

            spec = specs.get(spec_id)

            if spec is None:
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"Unknown attribute spec_id={spec_id}",
                    )
                )
                continue

            input_type = _enum_value(
                getattr(spec, "input_type", None)
            )

            if input_type == "checkbox" and value.lower() not in {
                "true",
                "false",
            }:
                issues.append(
                    (
                        shape_id,
                        frame_id,
                        "ERROR",
                        f"{spec.name} must be true/false, got '{value}'",
                    )
                )

    if not issues:
        console.print(
            f"[green bold]Validation OK[/green bold] "
            f"({len(shapes)} shapes checked)"
        )
        return 0

    table = Table(title=f"Task {task_id} annotation issues")
    table.add_column("ID", justify="right")
    table.add_column("Frame", justify="right")
    table.add_column("Level")
    table.add_column("Issue")

    for shape_id, frame_id, level, message in issues:
        table.add_row(
            str(shape_id),
            str(frame_id),
            level,
            message,
        )

    console.print(table)
    console.print(
        f"[red bold]{len(issues)} issue(s)[/red bold] "
        f"across {len(shapes)} checked shapes"
    )

    return len(issues)
