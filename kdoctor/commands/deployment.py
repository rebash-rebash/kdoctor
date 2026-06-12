import typer

from kdoctor.analyzers.deployment_analyzer import (
    analyze_deployment,
    analyze_all_deployments
)
from kdoctor.analyzers.deployment_investigator import ( investigate_deployment )
from kdoctor.analyzers.deployment_rollout import show_rollout_history
from kdoctor.analyzers.deployment_diff import compare_revisions

deployment = typer.Typer()


@deployment.command("analyze")
def analyze(
    name: str,
    namespace: str = "default"
):
    analyze_deployment(
        name,
        namespace
    )

@deployment.command("analyze-all")
def analyze_all(
    namespace: str = "default"
):
    analyze_all_deployments(
        namespace
    )

@deployment.command("investigate")
def investigate(
    name: str,
    namespace: str = "default",
    deep: bool = False
):
    investigate_deployment(
        name,
        namespace,
        deep
    )

@deployment.command("rollout-history")
def rollout_history(
    name: str,
    namespace: str = "default"
):
    show_rollout_history(
        name,
        namespace
    )

@deployment.command("diff")
def diff(
    name: str,
    revision1: str,
    revision2: str,
    namespace: str = "default"
):
    compare_revisions(
        name,
        namespace,
        revision1,
        revision2
    )