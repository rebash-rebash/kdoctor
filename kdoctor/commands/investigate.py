import typer

from kdoctor.analyzers.investigate_analyzer import investigate_pod

investigate = typer.Typer()


@investigate.command("pod")
def pod(
    name: str,
    namespace: str = "default"
):
    investigate_pod(
        name,
        namespace
    )