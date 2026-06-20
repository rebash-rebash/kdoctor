import typer

from kdoctor.analyzers.investigate_analyzer import investigate_pod

investigate = typer.Typer()


@investigate.command("pod")
def pod(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n")
):
    investigate_pod(
        name,
        namespace
    )
