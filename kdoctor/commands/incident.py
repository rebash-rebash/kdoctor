import typer

from kdoctor.analyzers.incident_analyzer import investigate_incident

incident = typer.Typer()


@incident.command("investigate")
def investigate(
    timeout: int = typer.Option(
        15, "--timeout", min=1, help="Per-request Kubernetes API timeout in seconds."
    )
):
    investigate_incident(timeout)
