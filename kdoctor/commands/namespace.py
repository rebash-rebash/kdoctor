import typer

from kdoctor.analyzers.namespace_analyzer import analyze_namespace

namespace = typer.Typer()


@namespace.command("analyze")
def analyze(
    name: str
):
    analyze_namespace(name)