import typer

from kdoctor.analyzers.namespace_analyzer import analyze_namespace
from kdoctor.analyzers.namespace_analyzer import investigate_namespace

namespace = typer.Typer()


@namespace.command("analyze")
def analyze(
    name: str,
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    analyze_namespace(name, output)


@namespace.command("investigate")
def investigate(
    name: str,
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    investigate_namespace(name, output)
