import typer

from kdoctor.analyzers.cluster_analyzer import (
    analyze_cluster,
    analyze_hotspots
)

cluster = typer.Typer()


@cluster.command("analyze")
def analyze(
    details: bool = False
):
    analyze_cluster(
        details=details
    )

@cluster.command("hotspots")
def hotspots():
    analyze_hotspots()