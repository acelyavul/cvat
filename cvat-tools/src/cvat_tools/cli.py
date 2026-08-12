import typer
from rich.console import Console

from .annotations import (
    add_box,
    bulk_delete_shapes,
    delete_shape,
    list_annotations,
    update_shape,
)
from .client import get_client
from .decisions import record_decision
from .drawing import render_frame
from .frames import save_frame
from .labels import show_labels
from .policy import policy_info, read_policy
from .progress import build_review_progress
from .review import (
    build_annotation_review,
    build_frame_review,
    build_next_review_context,
    build_task_review,
)
from .state import frame_annotation_sha256
from .polygons import add_polygon, build_polygon_review, parse_points, update_polygon
from .tasks import list_tasks, show_task
from .validation import validate_task_annotations

app = typer.Typer(
    name="cvat-tools",
    no_args_is_help=True,
)

tasks_app = typer.Typer(no_args_is_help=True)
annotations_app = typer.Typer(no_args_is_help=True)
labels_app = typer.Typer(no_args_is_help=True)
frame_app = typer.Typer(no_args_is_help=True)
box_app = typer.Typer(no_args_is_help=True)
review_app = typer.Typer(no_args_is_help=True)
policy_app = typer.Typer(no_args_is_help=True)
polygon_app = typer.Typer(no_args_is_help=True)

app.add_typer(tasks_app, name="tasks")
app.add_typer(annotations_app, name="annotations")
app.add_typer(labels_app, name="labels")
app.add_typer(frame_app, name="frame")
app.add_typer(box_app, name="box")
app.add_typer(review_app, name="review")
app.add_typer(policy_app, name="policy")
app.add_typer(polygon_app, name="polygon")

console = Console()


@app.command("status")
def status():
    """Test CVAT connection and authentication."""
    try:
        with get_client() as client:
            tasks = client.tasks.list()
            console.print(
                "[green]CVAT connection OK[/green] "
                f"({len(tasks)} tasks visible)"
            )
    except Exception as exc:  # noqa: BLE001
        console.print(
            f"[red]CVAT connection failed:[/red] {exc}"
        )
        raise typer.Exit(1)


@tasks_app.command("list")
def tasks_list():
    """List visible CVAT tasks."""
    with get_client() as client:
        list_tasks(client)


@tasks_app.command("show")
def tasks_show(task_id: int):
    """Show task details and labels."""
    with get_client() as client:
        show_task(client, task_id)


@labels_app.command("show")
def labels_show(task_id: int):
    """Show task labels and attribute specifications."""
    with get_client() as client:
        show_labels(client, task_id)


@annotations_app.command("list")
def annotations_list(
    task_id: int,
    frame: int | None = typer.Option(
        None,
        "--frame",
        "-f",
    ),
):
    """List task annotations."""
    with get_client() as client:
        list_annotations(client, task_id, frame)


@frame_app.command("get")
def frame_get(
    task_id: int,
    frame: int,
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
    ),
):
    """Download a frame from CVAT."""
    with get_client() as client:
        path = save_frame(
            client,
            task_id,
            frame,
            output,
        )

    console.print(f"[green]Saved:[/green] {path}")


@frame_app.command("render")
def frame_render(
    task_id: int,
    frame: int,
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
    ),
):
    """Render rectangle and polygon annotations."""
    with get_client() as client:
        result = render_frame(
            client,
            task_id,
            frame,
            output,
        )

    console.print(
        f"[green]Rendered:[/green] {result['path']}"
    )
    console.print(
        f"Rectangles: {result['rectangles']}  "
        f"Polygons: {result['polygons']}  "
        f"Total: {result['total']}"
    )


@box_app.command("add")
def box_add(
    task_id: int,
    frame: int = typer.Option(..., "--frame"),
    label: str = typer.Option(..., "--label"),
    x1: float = typer.Option(..., "--x1"),
    y1: float = typer.Option(..., "--y1"),
    x2: float = typer.Option(..., "--x2"),
    y2: float = typer.Option(..., "--y2"),
    attr: list[str] = typer.Option(
        [],
        "--attr",
        help="Attribute NAME=VALUE. May be repeated.",
    ),
):
    """Create a rectangle annotation."""
    with get_client() as client:
        result = add_box(
            client,
            task_id,
            frame,
            label,
            x1,
            y1,
            x2,
            y2,
            attr,
        )

    console.print(
        "[green]Bounding box created[/green]"
    )
    console.print(f"ID: {result['id']}")
    console.print(f"Frame: {result['frame']}")
    console.print(
        f"Label: {result['label']} "
        f"({result['label_id']})"
    )
    console.print(
        f"Points: {result['points']}"
    )
    console.print(
        f"Attributes: {result['attributes']}"
    )


@annotations_app.command("delete")
def annotations_delete(
    task_id: int,
    annotation_id: int = typer.Option(..., "--id"),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Actually delete the annotation.",
    ),
):
    """Delete one standalone shape. Dry-run unless --yes is given."""
    with get_client() as client:
        deleted, item = delete_shape(
            client,
            task_id,
            annotation_id,
            yes=yes,
        )

    if not deleted:
        console.print("[yellow bold]DRY RUN[/yellow bold]")
        console.print("Would delete:")
    else:
        console.print("[green bold]Deleted and verified[/green bold]")

    console.print(f"ID: {item['id']}")
    console.print(f"Frame: {item['frame']}")
    console.print(
        f"Label: {item['label']} ({item['label_id']})"
    )
    console.print(f"Type: {item['type']}")
    console.print(f"Points: {item['points']}")
    console.print(f"Attributes: {item['attributes']}")


@annotations_app.command("validate")
def annotations_validate(
    task_id: int,
    frame: int | None = typer.Option(None, "--frame", "-f"),
):
    """Validate annotation structure without modifying CVAT."""
    with get_client() as client:
        count = validate_task_annotations(client, task_id, frame)

    if count:
        raise typer.Exit(2)


@review_app.command("frame")
def review_frame(task_id: int, frame: int):
    """Build a complete read-only annotation review packet."""
    with get_client() as client:
        result = build_frame_review(client, task_id, frame)

    console.print("[green]Review packet created[/green]")
    console.print(f"Directory: {result['directory']}")
    console.print(f"Annotations: {result['count']}")


@annotations_app.command("update")
def annotations_update(
    task_id: int,
    annotation_id: int = typer.Option(..., "--id"),
    x1: float | None = typer.Option(None, "--x1"),
    y1: float | None = typer.Option(None, "--y1"),
    x2: float | None = typer.Option(None, "--x2"),
    y2: float | None = typer.Option(None, "--y2"),
    attr: list[str] = typer.Option([], "--attr"),
    yes: bool = typer.Option(False, "--yes"),
):
    """Update one standalone rectangle. Dry-run unless --yes."""
    with get_client() as client:
        changed, before, after = update_shape(
            client,
            task_id,
            annotation_id,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            attribute_args=attr,
            yes=yes,
        )

    if changed:
        console.print("[green bold]Updated and verified[/green bold]")
    else:
        console.print("[yellow bold]DRY RUN[/yellow bold]")

    console.print(f"ID: {before['id']}")
    console.print(f"Before points: {before['points']}")
    console.print(f"After points:  {after['points']}")
    console.print(f"Before attrs: {before['attributes']}")
    console.print(f"After attrs:  {after['attributes']}")


@review_app.command("task")
def review_task(task_id: int):
    """Build a read-only task annotation review manifest."""
    with get_client() as client:
        result = build_task_review(client, task_id)

    console.print("[green]Task review created[/green]")
    console.print(f"Manifest: {result['manifest']}")
    console.print(f"Annotated frames: {result['annotated_frames']}")
    console.print(f"Shapes: {result['shapes']}")
    console.print(f"Tracks: {result['tracks']}")


@review_app.command("annotation")
def review_annotation(
    task_id: int,
    annotation_id: int = typer.Option(..., "--id"),
):
    """Build a read-only visual review packet for one annotation."""
    with get_client() as client:
        result = build_annotation_review(
            client,
            task_id,
            annotation_id,
        )

    console.print("[green]Annotation review created[/green]")
    console.print(f"Directory: {result['directory']}")
    console.print(f"Frame: {result['frame']}")
    console.print(f"Label: {result['label']}")
    console.print(f"Attributes: {result['attributes']}")


@annotations_app.command("delete-filtered")
def annotations_delete_filtered(
    task_id: int,
    frame: int | None = typer.Option(None, "--frame"),
    label: str | None = typer.Option(None, "--label"),
    shape_type: str | None = typer.Option(None, "--type"),
    yes: bool = typer.Option(False, "--yes"),
):
    """Delete filtered standalone shapes. Dry-run unless --yes."""
    with get_client() as client:
        deleted, items = bulk_delete_shapes(
            client,
            task_id,
            frame=frame,
            label_name=label,
            shape_type=shape_type,
            yes=yes,
        )

    if deleted:
        console.print("[green bold]Deleted and verified[/green bold]")
    else:
        console.print("[yellow bold]DRY RUN[/yellow bold]")

    console.print(f"Matched shapes: {len(items)}")

    for item in items:
        console.print(
            f"#{item['id']} frame={item['frame']} "
            f"label={item['label']} type={item['type']}"
        )


@review_app.command("decide")
def review_decide(
    task_id: int,
    frame: int = typer.Option(..., "--frame"),
    status: str = typer.Option(..., "--status"),
    reason: str = typer.Option(..., "--reason"),
    action: str = typer.Option("none", "--action"),
    annotation_id: list[int] = typer.Option([], "--id"),
):
    """Record a local policy review decision without modifying CVAT."""
    with get_client() as client:
        task = client.tasks.retrieve(task_id)
        annotations = task.get_annotations()

        annotation_sha256 = frame_annotation_sha256(
            annotations,
            frame,
        )

    path, result = record_decision(
        task_id=task_id,
        frame=frame,
        status=status,
        reason=reason,
        action=action,
        annotation_ids=annotation_id,
        annotation_sha256=annotation_sha256,
    )

    console.print(
        f"[green]Decision recorded[/green]: "
        f"{result['status']} frame={result['frame']}"
    )
    console.print(f"Annotation SHA256: {annotation_sha256}")
    console.print(f"File: {path}")


@policy_app.command("show")
def policy_show():
    """Print the active annotation policy."""
    console.print(read_policy())


@policy_app.command("info")
def policy_information():
    """Show active annotation policy path and fingerprint."""
    info = policy_info()
    console.print(f"Path: {info['path']}")
    console.print(f"SHA256: {info['sha256']}")
    console.print(f"Bytes: {info['bytes']}")


@review_app.command("progress")
def review_progress(
    task_id: int,
    limit: int = typer.Option(20, "--limit"),
):
    """Show review progress and next frames without modifying CVAT."""
    with get_client() as client:
        path, result = build_review_progress(
            client,
            task_id,
            limit=limit,
        )

    console.print(f"Frames: {result['frame_count']}")
    console.print(
        f"PASS={result['status_counts']['PASS']} "
        f"REVIEW={result['status_counts']['REVIEW']} "
        f"FAIL={result['status_counts']['FAIL']}"
    )
    console.print(
        f"Stale policy decisions: "
        f"{len(result['stale_policy_frames'])}"
    )
    console.print(
        f"Stale annotation decisions: "
        f"{len(result['stale_annotation_frames'])}"
    )
    console.print(f"Pending: {result['pending_count']}")
    console.print(f"Next: {result['next_frames']}")
    console.print(f"Progress file: {path}")

    if result["complete"]:
        console.print("[green bold]Review complete[/green bold]")


@review_app.command("next")
def review_next(task_id: int):
    """Prepare the next pending frame for policy review."""
    with get_client() as client:
        result = build_next_review_context(
            client,
            task_id,
        )

    if result is None:
        console.print(
            "[green bold]Review complete[/green bold]"
        )
        return

    console.print(
        "[green]Review context created[/green]"
    )
    console.print(f"Frame: {result['frame']}")
    console.print(
        f"Annotations: {result['annotation_count']}"
    )
    console.print(f"Context: {result['context']}")
    console.print(f"Original: {result['original']}")
    console.print(f"Annotated: {result['annotated']}")
    console.print(
        f"Policy SHA256: {result['policy_sha256']}"
    )


@polygon_app.command("add")
def polygon_add(
    task_id: int,
    frame: int = typer.Option(..., "--frame"),
    label: str = typer.Option(
        "privacy_region",
        "--label",
    ),
    point: list[str] = typer.Option(
        [],
        "--point",
    ),
    yes: bool = typer.Option(False, "--yes"),
):
    """Create a standalone polygon. Dry-run unless --yes."""
    points = parse_points(point)

    with get_client() as client:
        changed, result = add_polygon(
            client,
            task_id,
            frame,
            label,
            points,
            yes=yes,
        )

    if changed:
        console.print(
            "[green bold]Polygon created and verified[/green bold]"
        )
        console.print(f"ID: {result['id']}")
    else:
        console.print(
            "[yellow bold]DRY RUN[/yellow bold]"
        )

    console.print(f"Frame: {result['frame']}")
    console.print(f"Label: {result['label']}")
    console.print(
        f"Vertices: {result['vertices']}"
    )
    console.print(f"Points: {result['points']}")


@polygon_app.command("update")
def polygon_update(
    task_id: int,
    annotation_id: int = typer.Option(
        ...,
        "--id",
    ),
    point: list[str] = typer.Option(
        [],
        "--point",
    ),
    yes: bool = typer.Option(False, "--yes"),
):
    """Replace polygon vertices. Dry-run unless --yes."""
    points = parse_points(point)

    with get_client() as client:
        changed, before, after = update_polygon(
            client,
            task_id,
            annotation_id,
            points,
            yes=yes,
        )

    if changed:
        console.print(
            "[green bold]Polygon updated and verified[/green bold]"
        )
    else:
        console.print(
            "[yellow bold]DRY RUN[/yellow bold]"
        )

    console.print(f"ID: {annotation_id}")
    console.print(
        f"Before: {before['points']}"
    )
    console.print(
        f"After:  {after['points']}"
    )


@polygon_app.command("review")
def polygon_review(
    task_id: int,
    annotation_id: int = typer.Option(
        ...,
        "--id",
    ),
):
    """Create a visual crop for one polygon."""
    with get_client() as client:
        result = build_polygon_review(
            client,
            task_id,
            annotation_id,
        )

    console.print(
        "[green]Polygon review created[/green]"
    )
    console.print(f"Frame: {result['frame']}")
    console.print(
        f"Original: {result['original']}"
    )
    console.print(
        f"Polygon: {result['polygon']}"
    )


if __name__ == "__main__":
    app()
