from typing import Optional

from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1, get_core_v1
from kdoctor.utils.kube import (
    deployment_pods,
    deployment_replicasets,
    oom_events,
    revision_label,
    revision_number,
    total_restarts
)
from kdoctor.utils.output import console, render


def advise_rollback(
    deployment_name: str,
    namespace: str,
    output_format: Optional[str] = None
):
    try:
        apps = get_apps_v1()
        core = get_core_v1()
        deployment = apps.read_namespaced_deployment(
            deployment_name,
            namespace
        )
        replicasets = deployment_replicasets(
            apps,
            deployment,
            namespace
        )
        pods = deployment_pods(core, deployment, namespace)
    except Exception as e:
        console.print(
            f"[red]Failed to analyze rollback safety:[/red] {e}"
        )
        return

    if len(replicasets) < 2:
        console.print(
            "[yellow]Rollback advisor requires at least two revisions[/yellow]"
        )
        return

    current = replicasets[0]
    previous = replicasets[1]
    reasons = build_rollback_reasons(current, previous, pods)
    safe = is_safe_to_rollback(deployment, pods, reasons)

    payload = {
        "deployment": f"{namespace}/{deployment.metadata.name}",
        "safe_to_rollback": safe,
        "current_revision": revision_number(current),
        "rollback_target": revision_number(previous),
        "reasons": reasons,
        "recommended_revision_label": revision_label(previous),
        "current_revision_label": revision_label(current),
    }

    if output_format:
        render(payload, output_format)
        return

    print_rollback_summary(
        safe,
        deployment,
        current,
        previous,
        reasons
    )


def build_rollback_reasons(current, previous, pods):
    reasons = []

    restarts = sum(total_restarts(pod) for pod in pods)
    ooms = sum(oom_events(pod) for pod in pods)

    if restarts > 0:
        reasons.append("Restart count increased")

    if ooms > 0:
        reasons.append("OOM events increased")

    current_container = current.spec.template.spec.containers[0]
    previous_container = previous.spec.template.spec.containers[0]

    if current_container.image != previous_container.image:
        reasons.append("Container image changed")

    if (
        resource_requests(current_container)
        != resource_requests(previous_container)
    ):
        reasons.append("Resource requests changed")

    if (
        resource_limits(current_container)
        != resource_limits(previous_container)
    ):
        reasons.append("Resource limits changed")

    current_env = {
        env.name: env.value
        for env in current_container.env or []
    }
    previous_env = {
        env.name: env.value
        for env in previous_container.env or []
    }

    if current_env != previous_env:
        reasons.append("Environment variables changed")

    return reasons


def resource_requests(container):
    return (
        container.resources.requests
        if container.resources and container.resources.requests
        else {}
    )


def resource_limits(container):
    return (
        container.resources.limits
        if container.resources and container.resources.limits
        else {}
    )


def is_safe_to_rollback(deployment, pods, reasons):
    desired = deployment.spec.replicas or 0
    available = deployment.status.available_replicas or 0

    if desired and available == 0:
        return False

    if not reasons:
        return False

    unavailable = desired - available
    if unavailable > max(1, desired // 2):
        return False

    return True


def print_rollback_summary(
    safe,
    deployment,
    current,
    previous,
    reasons
):
    status = "SAFE TO ROLLBACK" if safe else "ROLLBACK NEEDS REVIEW"
    status_style = "green" if safe else "yellow"

    console.print(
        f"[bold {status_style}]{status}[/bold {status_style}]"
    )
    console.print()
    console.print(
        f"Current Revision: {revision_label(current)}"
    )
    console.print(
        f"Recommended Revision: {revision_label(previous)}"
    )

    table = Table(title="Safety Assessment")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Deployment", deployment.metadata.name)
    table.add_row(
        "Desired Replicas",
        str(deployment.spec.replicas or 0)
    )
    table.add_row(
        "Available Replicas",
        str(deployment.status.available_replicas or 0)
    )
    table.add_row(
        "Current Revision",
        str(revision_number(current))
    )
    table.add_row(
        "Rollback Target",
        str(revision_number(previous))
    )

    console.print()
    console.print(table)

    console.print()
    console.print("[bold cyan]Reasons[/bold cyan]")

    if not reasons:
        console.print("- No regression evidence found")
        return

    for reason in reasons:
        console.print(f"- {reason}")
