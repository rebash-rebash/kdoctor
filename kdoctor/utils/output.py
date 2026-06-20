import json

import yaml
from rich.console import Console
from rich.table import Table

console = Console()


def print_header(title: str, data: dict):
    table = Table(title=title)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    for name, value in data.items():
        table.add_row(str(name), str(value))

    console.print(table)


def render(data, output_format: str):
    output_format = (output_format or "").lower()

    if output_format == "json":
        console.print(json.dumps(data, indent=2))
        return True

    if output_format == "yaml":
        console.print(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
        return True

    return False


def print_error(message: str):
    console.print(f"[red]{message}[/red]")


def print_warning(message: str):
    console.print(f"[yellow]{message}[/yellow]")


def print_success(message: str):
    console.print(f"[green]{message}[/green]")
