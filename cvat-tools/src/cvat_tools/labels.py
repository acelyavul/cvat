from rich.console import Console
from rich.table import Table

console = Console()


def _value(value):
    return getattr(value, "value", value)


def show_labels(client, task_id: int):
    task = client.tasks.retrieve(task_id)
    labels = task.get_labels()

    for label in labels:
        console.print(
            f"\n[bold cyan]Label:[/bold cyan] "
            f"{label.name}  [dim](id={label.id})[/dim]"
        )

        console.print(
            f"Type: {_value(getattr(label, 'type', '-'))}"
        )

        attrs = list(getattr(label, "attributes", []) or [])

        if not attrs:
            console.print("[dim]No attributes[/dim]")
            continue

        table = Table(title=f"{label.name} attributes")
        table.add_column("Spec ID", justify="right")
        table.add_column("Name")
        table.add_column("Input Type")
        table.add_column("Mutable")
        table.add_column("Default")
        table.add_column("Values")

        for attr in attrs:
            table.add_row(
                str(getattr(attr, "id", "-")),
                str(getattr(attr, "name", "-")),
                str(_value(getattr(attr, "input_type", "-"))),
                str(getattr(attr, "mutable", "-")),
                str(getattr(attr, "default_value", "-")),
                ", ".join(
                    str(v)
                    for v in (getattr(attr, "values", []) or [])
                ),
            )

        console.print(table)
