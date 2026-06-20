import typer

from kdoctor.analyzers.deployment_analyzer import (
    analyze_deployment,
    analyze_all_deployments
)
from kdoctor.analyzers.deployment_investigator import ( investigate_deployment )
from kdoctor.analyzers.deployment_rollout import show_rollout_history
from kdoctor.analyzers.deployment_diff import compare_revisions
from kdoctor.analyzers.deployment_rollback_advisor import advise_rollback
from kdoctor.analyzers.deployment_drift import detect_deployment_drift
from kdoctor.analyzers.deployment_audit import audit_deployment
from kdoctor.analyzers.deployment_rca import analyze_deployment_rca

deployment = typer.Typer()


@deployment.command("analyze")
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
    analyze_deployment(
        name,
        namespace,
        output
    )

@deployment.command("analyze-all")
def analyze_all(
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    analyze_all_deployments(
        namespace,
        output
    )

@deployment.command("investigate")
def investigate(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    deep: bool = False,
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    investigate_deployment(
        name,
        namespace,
        deep,
        output
    )

@deployment.command("rollout-history")
def rollout_history(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    show_rollout_history(
        name,
        namespace,
        output
    )

@deployment.command("diff")
def diff(
    name: str,
    revision1: str,
    revision2: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    compare_revisions(
        name,
        namespace,
        revision1,
        revision2,
        output
    )


@deployment.command("rollback-advisor")
def rollback_advisor(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    advise_rollback(
        name,
        namespace,
        output
    )


@deployment.command("drift")
def drift(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    detect_deployment_drift(
        name,
        namespace,
        output
    )


@deployment.command("audit")
def audit(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json or yaml"
    )
):
    audit_deployment(
        name,
        namespace,
        output
    )


@deployment.command("rca")
def rca(
    name: str,
    namespace: str = typer.Option("default", "--namespace", "-n")
):
    analyze_deployment_rca(
        name,
        namespace
    )
