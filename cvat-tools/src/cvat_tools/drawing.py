from pathlib import Path

from PIL import ImageDraw, ImageFont

from .frames import get_frame_image


def _enum_value(value):
    return getattr(value, "value", value)


def _label_maps(task):
    labels = list(task.get_labels())

    names = {
        label.id: label.name
        for label in labels
    }

    return names


def _text_size(draw, text, font):
    box = draw.textbbox(
        (0, 0),
        text,
        font=font,
    )

    return (
        box[2] - box[0],
        box[3] - box[1],
    )


def _draw_label(
    draw,
    x: float,
    y: float,
    text: str,
    font,
):
    width, height = _text_size(
        draw,
        text,
        font,
    )

    left = max(0, int(x))
    top = max(0, int(y) - height - 8)

    draw.rectangle(
        (
            left,
            top,
            left + width + 8,
            top + height + 6,
        ),
        fill="black",
    )

    draw.text(
        (left + 4, top + 3),
        text,
        fill="white",
        font=font,
    )


def render_frame(
    client,
    task_id: int,
    frame: int,
    output_path: str | None = None,
    show_ids: bool = True,
):
    task = client.tasks.retrieve(task_id)
    annotations = task.get_annotations()

    image = get_frame_image(
        client,
        task_id,
        frame,
        quality="original",
    ).convert("RGB")

    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    labels = _label_maps(task)

    rectangles = 0
    polygons = 0

    for shape in (
        getattr(annotations, "shapes", []) or []
    ):
        if getattr(shape, "frame", None) != frame:
            continue

        shape_type = _enum_value(
            getattr(shape, "type", None)
        )

        points = list(
            getattr(shape, "points", []) or []
        )

        annotation_id = getattr(
            shape,
            "id",
            None,
        )

        label_name = labels.get(
            getattr(shape, "label_id", None),
            f"label_{getattr(shape, 'label_id', '?')}",
        )

        text = label_name

        if show_ids and annotation_id is not None:
            text += f" #{annotation_id}"

        if shape_type == "rectangle":
            if len(points) != 4:
                continue

            x1, y1, x2, y2 = points

            draw.rectangle(
                (x1, y1, x2, y2),
                outline="red",
                width=5,
            )

            _draw_label(
                draw,
                x1,
                y1,
                text,
                font,
            )

            rectangles += 1

        elif shape_type == "polygon":
            if len(points) < 6 or len(points) % 2:
                continue

            vertices = list(
                zip(
                    points[0::2],
                    points[1::2],
                    strict=True,
                )
            )

            # Review visualization only.
            # This does not alter CVAT/source pixels.
            draw.polygon(
                vertices,
                outline="yellow",
                width=5,
            )

            x = min(
                point[0]
                for point in vertices
            )
            y = min(
                point[1]
                for point in vertices
            )

            _draw_label(
                draw,
                x,
                y,
                text,
                font,
            )

            polygons += 1

    path = Path(
        output_path
        or f"output/task_{task_id}_frame_{frame}_annotated.jpg"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.save(
        path,
        quality=95,
    )

    return {
        "path": path,
        "rectangles": rectangles,
        "polygons": polygons,
        "total": rectangles + polygons,
    }
