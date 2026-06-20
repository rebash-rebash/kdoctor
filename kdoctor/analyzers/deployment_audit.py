from typing import Optional

from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1
from kdoctor.utils.kube import SYSTEM_CONTAINERS, image_tag
from kdoctor.utils.output import console, render
from kdoctor.utils.risk import RiskEngine, risk_from_score, score_style


def audit_deployment(
    deployment_name: str,
    namespace: str,
    output_format: Optional[str] = None
):
    try:
        apps = get_apps_v1()
        deployment = apps.read_namespaced_deployment(
            deployment_name,
            namespace
        )
    except Exception as e:
        console.print(
            f"[red]Failed to audit deployment:[/red] {e}"
        )
        return

    result = evaluate_deployment(deployment)

    if output_format:
        payload = {
            "deployment": f"{namespace}/{deployment.metadata.name}",
            "score": result["score"],
            "risk": result["risk"],
            "findings": result["findings"],
        }
        render(payload, output_format)
        return

    print_audit_report(deployment, namespace, result)


def evaluate_deployment(deployment):
    risk = RiskEngine()
    findings = []

    pod_security_context = deployment.spec.template.spec.security_context

    for container in deployment.spec.template.spec.containers:
        if container.name in SYSTEM_CONTAINERS:
            continue

        resources = container.resources
        requests = resources.requests if resources else None
        limits = resources.limits if resources else None
        security_context = container.security_context

        add_finding(
            findings,
            risk,
            not requests,
            8,
            container.name,
            "Missing requests"
        )
        add_finding(
            findings,
            risk,
            not limits,
            8,
            container.name,
            "Missing limits"
        )
        add_finding(
            findings,
            risk,
            not container.liveness_probe,
            6,
            container.name,
            "Missing liveness probe"
        )
        add_finding(
            findings,
            risk,
            not container.readiness_probe,
            6,
            container.name,
            "Missing readiness probe"
        )
        add_finding(
            findings,
            risk,
            not container.startup_probe,
            3,
            container.name,
            "Missing startup probe"
        )
        add_finding(
            findings,
            risk,
            not security_context and not pod_security_context,
            5,
            container.name,
            "Missing security context"
        )
        add_finding(
            findings,
            risk,
            runs_as_root(security_context, pod_security_context),
            10,
            container.name,
            "Running as root"
        )
        add_finding(
            findings,
            risk,
            security_context
            and security_context.privileged is True,
            15,
            container.name,
            "Privileged container"
        )
        add_finding(
            findings,
            risk,
            image_tag(container.image) == "latest",
            7,
            container.name,
            "Uses latest image tag"
        )
        add_finding(
            findings,
            risk,
            ":" not in container.image.rsplit("/", 1)[-1],
            5,
            container.name,
            "Image tag omitted"
        )

    result = risk.result()
    result["findings"] = findings
    return result


def add_finding(findings, risk, condition, points, container, message):
    if not condition:
        return

    findings.append(
        {
            "container": container,
            "finding": message,
            "points": points
        }
    )
    risk.penalize(points, f"{container}: {message}")


def runs_as_root(container_context, pod_context):
    if container_context and container_context.run_as_non_root is True:
        return False

    if pod_context and pod_context.run_as_non_root is True:
        return False

    if (
        container_context
        and container_context.run_as_user is not None
    ):
        return container_context.run_as_user == 0

    if pod_context and pod_context.run_as_user is not None:
        return pod_context.run_as_user == 0

    return True


def print_audit_report(deployment, namespace, result):
    score = result["score"]
    console.print(
        f"[bold blue]Score:[/bold blue] "
        f"[{score_style(score)}]{score}/100[/]"
    )
    console.print(
        f"[bold blue]Risk:[/bold blue] {risk_from_score(score)}"
    )

    table = Table(
        title=f"Deployment Audit ({namespace}/{deployment.metadata.name})"
    )
    table.add_column("Container")
    table.add_column("Finding")
    table.add_column("Penalty")

    for finding in result["findings"]:
        table.add_row(
            finding["container"],
            finding["finding"],
            str(finding["points"])
        )

    console.print()

    if result["findings"]:
        console.print(table)
    else:
        console.print("[green]No audit findings detected[/green]")
