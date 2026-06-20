from typing import Optional

from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1
from kdoctor.utils.kube import (configmap_refs, container_env,
                                deployment_replicasets, secret_refs)
from kdoctor.utils.output import console, render


def detect_deployment_drift(
    deployment_name: str, namespace: str, output_format: Optional[str] = None
):
    try:
        apps = get_apps_v1()
        deployment = apps.read_namespaced_deployment(deployment_name, namespace)
        replicasets = deployment_replicasets(apps, deployment, namespace)
    except Exception as e:
        console.print(f"[red]Failed to detect deployment drift:[/red] {e}")
        return

    if not replicasets:
        console.print("[yellow]No ReplicaSets found for deployment[/yellow]")
        return

    expected = replicasets[0]
    findings = compare_live_to_replicaset(deployment, expected)

    if output_format:
        payload = {
            "deployment": f"{namespace}/{deployment_name}",
            "expected_source": expected.metadata.name,
            "drift_detected": bool(findings),
            "findings": findings,
        }
        render(payload, output_format)
        return

    print_drift_report(deployment_name, namespace, expected.metadata.name, findings)


def compare_live_to_replicaset(deployment, replicaset):
    findings = []

    compare_field(
        findings, "spec.replicas", replicaset.spec.replicas, deployment.spec.replicas
    )

    live_containers = {
        container.name: container
        for container in deployment.spec.template.spec.containers
    }
    expected_containers = {
        container.name: container
        for container in replicaset.spec.template.spec.containers
    }

    for name in sorted(set(live_containers.keys()) | set(expected_containers.keys())):
        live = live_containers.get(name)
        expected = expected_containers.get(name)

        if not live or not expected:
            compare_field(
                findings,
                f"containers.{name}",
                "present" if expected else "missing",
                "present" if live else "missing",
            )
            continue

        compare_field(findings, f"containers.{name}.image", expected.image, live.image)
        compare_field(
            findings,
            f"containers.{name}.env",
            container_env(expected),
            container_env(live),
        )
        compare_field(
            findings,
            f"containers.{name}.resources.requests",
            resource_requests(expected),
            resource_requests(live),
        )
        compare_field(
            findings,
            f"containers.{name}.resources.limits",
            resource_limits(expected),
            resource_limits(live),
        )
        compare_field(
            findings,
            f"containers.{name}.configmaps",
            configmap_refs(expected),
            configmap_refs(live),
        )
        compare_field(
            findings,
            f"containers.{name}.secrets",
            secret_refs(expected),
            secret_refs(live),
        )

    return findings


def compare_field(findings, field, expected, actual):
    if expected == actual:
        return

    findings.append({"field": field, "expected": expected, "actual": actual})


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


def print_drift_report(deployment_name, namespace, replicaset_name, findings):
    if findings:
        console.print("[bold red]Drift Detected[/bold red]")
    else:
        console.print("[bold green]No Drift Detected[/bold green]")

    console.print(f"Deployment: {namespace}/{deployment_name}")
    console.print(f"Expected Source: ReplicaSet {replicaset_name}")

    if not findings:
        return

    table = Table(title="Drift Findings")
    table.add_column("Field", style="cyan")
    table.add_column("Expected", overflow="fold")
    table.add_column("Actual", overflow="fold")

    for finding in findings:
        table.add_row(
            finding["field"], str(finding["expected"]), str(finding["actual"])
        )

    console.print()
    console.print(table)
