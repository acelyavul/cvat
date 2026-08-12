from pathlib import Path

from PIL import ImageDraw
from cvat_sdk.api_client.models import (
    LabeledShapeRequest,
    PatchedLabeledDataRequest,
    ShapeType,
)

from .frames import get_frame_image


def _enum_value(value):
    return getattr(value, "value", value)


def _find_label(task, label_name: str):
    for label in task.get_labels():
        if label.name == label_name:
            return label

    raise ValueError(
        f"Label '{label_name}' not found in task {task.id}"
    )


def _find_polygon(task, annotation_id: int):
    annotations = task.get_annotations()

    for shape in getattr(annotations, "shapes", []) or []:
        if getattr(shape, "id", None) != annotation_id:
            continue

        shape_type = _enum_value(
            getattr(shape, "type", None)
        )

        if shape_type != "polygon":
            raise ValueError(
                f"Annotation {annotation_id} is "
                f"'{shape_type}', not polygon."
            )

        return shape

    raise ValueError(
        f"Polygon annotation {annotation_id} not found."
    )


def parse_points(values: list[str]) -> list[float]:
    if len(values) < 3:
        raise ValueError(
            "A polygon requires at least 3 points."
        )

    points = []

    for value in values:
        if "," not in value:
            raise ValueError(
                f"Invalid point '{value}'. Expected X,Y."
            )

        x_raw, y_raw = value.split(",", 1)

        try:
            x = float(x_raw.strip())
            y = float(y_raw.strip())
        except ValueError as exc:
            raise ValueError(
                f"Invalid point '{value}'. Expected numeric X,Y."
            ) from exc

        points.extend([x, y])

    return points


def _pairs(points: list[float]):
    return list(zip(points[0::2], points[1::2], strict=True))


def _polygon_area(points: list[float]) -> float:
    pairs = _pairs(points)

    area = 0.0

    for index, (x1, y1) in enumerate(pairs):
        x2, y2 = pairs[(index + 1) % len(pairs)]
        area += x1 * y2 - x2 * y1

    return abs(area) / 2.0


def validate_polygon_points(
    points: list[float],
    width: int,
    height: int,
):
    if len(points) < 6 or len(points) % 2:
        raise ValueError(
            "Polygon requires at least 3 X,Y coordinate pairs."
        )

    for x, y in _pairs(points):
        if x < 0 or y < 0:
            raise ValueError(
                f"Negative polygon coordinate: ({x}, {y})"
            )

        if x > width or y > height:
            raise ValueError(
                f"Polygon point ({x}, {y}) is outside "
                f"frame {width}x{height}."
            )

    if _polygon_area(points) <= 0:
        raise ValueError(
            "Polygon area must be greater than zero."
        )


def _shape_request(
    shape,
    points: list[float],
):
    kwargs = {
        "type": ShapeType("polygon"),
        "label_id": shape.label_id,
        "frame": shape.frame,
        "points": points,
        "occluded": bool(
            getattr(shape, "occluded", False)
        ),
        "outside": bool(
            getattr(shape, "outside", False)
        ),
        "rotation": float(
            getattr(shape, "rotation", 0.0) or 0.0
        ),
        "z_order": int(
            getattr(shape, "z_order", 0) or 0
        ),
        "source": str(
            _enum_value(
                getattr(shape, "source", "manual")
            )
        ),
        "attributes": list(
            getattr(shape, "attributes", []) or []
        ),
    }

    annotation_id = getattr(shape, "id", None)

    if annotation_id is not None:
        kwargs["id"] = annotation_id

    group = getattr(shape, "group", None)

    if group is not None:
        kwargs["group"] = group

    return LabeledShapeRequest(**kwargs)


def add_polygon(
    client,
    task_id: int,
    frame: int,
    label_name: str,
    points: list[float],
    yes: bool = False,
):
    task = client.tasks.retrieve(task_id)
    label = _find_label(task, label_name)

    label_type = _enum_value(
        getattr(label, "type", None)
    )

    if label_type != "polygon":
        raise ValueError(
            f"Label '{label_name}' is type "
            f"'{label_type}', not polygon."
        )

    image = get_frame_image(
        client,
        task_id,
        frame,
        quality="original",
    )

    validate_polygon_points(
        points,
        image.width,
        image.height,
    )

    preview = {
        "task_id": task_id,
        "frame": frame,
        "label": label.name,
        "label_id": label.id,
        "type": "polygon",
        "points": points,
        "vertices": len(points) // 2,
    }

    if not yes:
        return False, preview

    before = task.get_annotations()

    before_ids = {
        shape.id
        for shape in (
            getattr(before, "shapes", []) or []
        )
        if getattr(shape, "id", None) is not None
    }

    request = LabeledShapeRequest(
        type=ShapeType("polygon"),
        label_id=label.id,
        frame=frame,
        points=points,
        source="manual",
    )

    client.api_client.tasks_api.partial_update_annotations(
        "create",
        task_id,
        patched_labeled_data_request=PatchedLabeledDataRequest(
            shapes=[request]
        ),
    )

    fresh = client.tasks.retrieve(task_id)
    annotations = fresh.get_annotations()

    created = [
        shape
        for shape in (
            getattr(annotations, "shapes", []) or []
        )
        if getattr(shape, "id", None) not in before_ids
        and getattr(shape, "frame", None) == frame
        and getattr(shape, "label_id", None) == label.id
        and _enum_value(
            getattr(shape, "type", None)
        ) == "polygon"
    ]

    if not created:
        raise RuntimeError(
            "Polygon creation could not be verified."
        )

    created.sort(
        key=lambda shape: shape.id or 0,
        reverse=True,
    )

    preview["id"] = created[0].id

    return True, preview


def update_polygon(
    client,
    task_id: int,
    annotation_id: int,
    points: list[float],
    yes: bool = False,
):
    task = client.tasks.retrieve(task_id)
    shape = _find_polygon(
        task,
        annotation_id,
    )

    image = get_frame_image(
        client,
        task_id,
        shape.frame,
        quality="original",
    )

    validate_polygon_points(
        points,
        image.width,
        image.height,
    )

    before = {
        "id": shape.id,
        "frame": shape.frame,
        "label_id": shape.label_id,
        "points": list(shape.points),
    }

    after = {
        **before,
        "points": points,
    }

    if not yes:
        return False, before, after

    request = _shape_request(
        shape,
        points,
    )

    client.api_client.tasks_api.partial_update_annotations(
        "update",
        task_id,
        patched_labeled_data_request=PatchedLabeledDataRequest(
            shapes=[request]
        ),
    )

    fresh_task = client.tasks.retrieve(task_id)
    updated = _find_polygon(
        fresh_task,
        annotation_id,
    )

    actual_points = list(updated.points)

    if actual_points != points:
        raise RuntimeError(
            "Polygon update verification failed."
        )

    after["points"] = actual_points

    return True, before, after


def build_polygon_review(
    client,
    task_id: int,
    annotation_id: int,
    padding: int = 80,
):
    task = client.tasks.retrieve(task_id)
    shape = _find_polygon(
        task,
        annotation_id,
    )

    points = list(shape.points)
    pairs = _pairs(points)

    image = get_frame_image(
        client,
        task_id,
        shape.frame,
        quality="original",
    ).convert("RGB")

    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]

    left = max(0, int(min(xs) - padding))
    top = max(0, int(min(ys) - padding))
    right = min(
        image.width,
        int(max(xs) + padding),
    )
    bottom = min(
        image.height,
        int(max(ys) + padding),
    )

    crop = image.crop(
        (left, top, right, bottom)
    )

    boxed = crop.copy()
    draw = ImageDraw.Draw(boxed)

    local_points = [
        (x - left, y - top)
        for x, y in pairs
    ]

    draw.polygon(
        local_points,
        outline="red",
        width=5,
    )

    out = Path(
        f"output/review/task_{task_id}/"
        f"polygon_{annotation_id}"
    )
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_path = out / "crop.jpg"
    polygon_path = out / "polygon.jpg"

    crop.save(
        original_path,
        quality=95,
    )

    boxed.save(
        polygon_path,
        quality=95,
    )

    return {
        "directory": out,
        "frame": shape.frame,
        "id": annotation_id,
        "points": points,
        "original": original_path,
        "polygon": polygon_path,
    }
