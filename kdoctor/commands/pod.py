import typer

from kdoctor.analyzers.pod_analyzer import analyze_pod, analyze_all_pods
pod = typer.Typer()


@pod.command()
def analyze(
    name: str,
    namespace: str = "default"
):
    analyze_pod(name, namespace)

@pod.command("analyze-all")
def analyze_all(
    namespace: str = "default"
):
    analyze_all_pods(
        namespace
    )

@pod.command("analyze-all")
def analyze_all(
    namespace: str = "default",
    critical_only: bool = False,
    warning_only: bool = False,
    top: int = 0
):
    analyze_all_pods(
        namespace=namespace,
        critical_only=critical_only,
        warning_only=warning_only,
        top=top
    )