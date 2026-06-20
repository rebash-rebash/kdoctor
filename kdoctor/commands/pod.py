import typer

from kdoctor.analyzers.pod_analyzer import analyze_pod, analyze_all_pods
pod = typer.Typer()


@pod.command()
def analyze(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    analyze_pod(
        name,
        namespace,
        output
    )

@pod.command("analyze-all")
def analyze_all(
    namespace: str = typer.Option("default", "--namespace", "-n"),
    critical_only: bool = False,
    warning_only: bool = False,
    top: int = 0,
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    analyze_all_pods(
        namespace=namespace,
        critical_only=critical_only,
        warning_only=warning_only,
        top=top,
        output_format=output
    )
