import typer

from kdoctor.analyzers.cluster_analyzer import (analyze_cluster,
                                                analyze_hotspots)

cluster = typer.Typer()


@cluster.command("analyze")
def analyze(
    details: bool = False,
    output: str = typer.Option(
        None, "--output", "-o", help="Output format: json or yaml"
    ),
):
    analyze_cluster(details=details, output_format=output)


@cluster.command("hotspots")
def hotspots(
    output: str = typer.Option(
        None, "--output", "-o", help="Output format: json or yaml"
    )
):
    analyze_hotspots(output)
