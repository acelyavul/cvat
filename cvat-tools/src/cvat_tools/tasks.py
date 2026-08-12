from rich.console import Console
from rich.table import Table

console = Console()


def _value(obj, name, default="-"):
    value = getattr(obj, name, None)

    if value is None:
        return default

    if hasattr(value, "id"):
        return getattr(value, "id", default)

    return value


def list_tasks(client):
    tasks = client.tasks.list()

    table = Table(title="CVAT Tasks")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Frames", justify="right")
    table.add_column("Owner")
    table.add_column("Assignee")
    table.add_column("Project", justify="right")

    for task in tasks:
        owner = getattr(task, "owner", None)
        assignee = getattr(task, "assignee", None)

        owner_name = (
            getattr(owner, "username", None)
            or getattr(owner, "id", None)
            or "-"
        )

        assignee_name = (
            getattr(assignee, "username", None)
            or getattr(assignee, "id", None)
            or "-"
        )

        table.add_row(
            str(_value(task, "id")),
            str(_value(task, "name")),
            str(_value(task, "status")),
            str(_value(task, "size")),
            str(owner_name),
            str(assignee_name),
            str(_value(task, "project_id")),
        )

    console.print(table)
    console.print(f"[bold]Total:[/bold] {len(tasks)}")


def show_task(client, task_id: int):
    task = client.tasks.retrieve(task_id)

    console.print(f"[bold]Task ID:[/bold] {task.id}")
    console.print(f"[bold]Name:[/bold] {getattr(task, 'name', '-')}")
    console.print(f"[bold]Status:[/bold] {getattr(task, 'status', '-')}")
    console.print(f"[bold]Frames:[/bold] {getattr(task, 'size', '-')}")
    console.print(
        f"[bold]Project ID:[/bold] {getattr(task, 'project_id', None) or '-'}"
    )

    owner = getattr(task, "owner", None)
    assignee = getattr(task, "assignee", None)

    console.print(
        "[bold]Owner:[/bold] "
        + str(
            getattr(owner, "username", None)
            or getattr(owner, "id", None)
            or "-"
        )
    )

    console.print(
        "[bold]Assignee:[/bold] "
        + str(
            getattr(assignee, "username", None)
            or getattr(assignee, "id", None)
            or "-"
        )
    )

    labels = task.get_labels()

    table = Table(title="Labels")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Type")

    for label in labels:
        table.add_row(
            str(getattr(label, "id", "-")),
            str(getattr(label, "name", "-")),
            str(getattr(label, "type", "-")),
        )

    console.print(table)
