from io import BytesIO
from pathlib import Path

from PIL import Image


def get_frame_bytes(client, task_id: int, frame: int, quality: str = "original") -> bytes:
    response = client.api_client.tasks_api.retrieve_data(
        task_id,
        "frame",
        number=frame,
        quality=quality,
        _parse_response=False,
    )

    # SDK versions may return either response directly or tuple-like results.
    if isinstance(response, tuple):
        response = response[-1]

    data = getattr(response, "data", response)

    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(
            f"Unexpected frame response type: {type(data).__name__}"
        )

    return bytes(data)


def get_frame_image(client, task_id: int, frame: int, quality: str = "original") -> Image.Image:
    data = get_frame_bytes(client, task_id, frame, quality)
    image = Image.open(BytesIO(data))
    image.load()
    return image


def save_frame(
    client,
    task_id: int,
    frame: int,
    output: str | None = None,
    quality: str = "original",
) -> Path:
    image = get_frame_image(client, task_id, frame, quality)

    if output is None:
        output = f"output/task_{task_id}_frame_{frame}.jpg"

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    image.convert("RGB").save(path, quality=95)

    return path
