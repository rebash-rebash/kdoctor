from typing import Optional

from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1, get_core_v1
from kdoctor.utils.kube import (
    deployment_pods,
    is_crash_looping,
    missing_resource_counts,
    oom_events,
    ready_containers,
    total_restarts
)
from kdoctor.utils.output import console, render
from kdoctor.utils.risk import (
    RecommendationEngine,
    RiskEngine,
    risk_from_score,
    score_style
)


def analyze_namespace(namespace, output_format: Optional[str] = None):
    investigate_namespace(namespace, output_format)


def investigate_namespace(namespace, output_format: Optional[str] = None):
    try:
        core = get_core_v1()
        apps = get_apps_v1()
        deployments = apps.list_namespaced_deployment(
            namespace=namespace
        ).items
        pods = core.list_namespaced_pod(
            namespace=namespace
        ).items
    except Exception as e:
        console.print(
            f"[red]Failed to investigate namespace:[/red] {e}"
        )
        return

    deployment_reports = [
        build_deployment_report(core, deployment, namespace)
        for deployment in deployments
    ]

    pod_report = build_pod_inventory(pods)
    summary = score_namespace(
        deployment_reports,
        pod_report
    )

    if output_format:
        payload = {
            "namespace": namespace,
            "summary": summary,
            "deployments": deployment_reports,
            "pod_inventory": pod_report,
            "recommendations": summary["recommendations"],
        }
        render(payload, output_format)
        return

    print_namespace_summary(
        namespace,
        deployments,
        pods,
        summary,
        pod_report
    )
    print_deployment_inventory(deployment_reports)
    print_pod_inventory(pods)
    print_restart_hotspots(deployment_reports)
    print_oom_hotspots(deployment_reports)
    print_top_problematic_workloads(deployment_reports)
    print_recommendations(summary["recommendations"])


def build_deployment_report(core, deployment, namespace):
    pods = deployment_pods(core, deployment, namespace)
    missing_requests = 0
    missing_limits = 0
    restarts = 0
    oom_count = 0
    crash_looping = 0
    not_ready = 0

    for pod in pods:
        pod_missing_requests, pod_missing_limits = (
            missing_resource_counts(pod)
        )
        ready, total = ready_containers(pod)

        missing_requests += pod_missing_requests
        missing_limits += pod_missing_limits
        restarts += total_restarts(pod)
        oom_count += oom_events(pod)
        crash_looping += 1 if is_crash_looping(pod) else 0
        not_ready += 1 if total and ready < total else 0

    desired = deployment.spec.replicas or 0
    ready_replicas = deployment.status.ready_replicas or 0
    available = deployment.status.available_replicas or 0

    risk = RiskEngine()
    risk.penalize(
        20 if ready_replicas < desired else 0,
        "Deployment has unavailable replicas"
    )
    risk.penalize(
        min(restarts * 2, 25),
        "Pods are restarting"
    )
    risk.penalize(
        oom_count * 10,
        "OOMKilled containers detected"
    )
    risk.penalize(
        crash_looping * 25,
        "CrashLoopBackOff detected"
    )
    risk.penalize(
        min((missing_requests + missing_limits) * 4, 20),
        "Resource requests or limits are missing"
    )

    result = risk.result()

    return {
        "name": deployment.metadata.name,
        "desired": desired,
        "ready": ready_replicas,
        "available": available,
        "pods": len(pods),
        "restarts": restarts,
        "oom": oom_count,
        "crash_looping": crash_looping,
        "missing_requests": missing_requests,
        "missing_limits": missing_limits,
        "not_ready": not_ready,
        "score": result["score"],
        "risk": result["risk"],
        "reasons": result["reasons"]
    }


def build_pod_inventory(pods):
    phases = {}
    restarts = 0
    oom_count = 0
    crash_looping = 0
    missing_requests = 0
    missing_limits = 0
    not_ready = 0

    for pod in pods:
        phase = pod.status.phase or "Unknown"
        phases[phase] = phases.get(phase, 0) + 1
        restarts += total_restarts(pod)
        oom_count += oom_events(pod)
        crash_looping += 1 if is_crash_looping(pod) else 0

        pod_missing_requests, pod_missing_limits = (
            missing_resource_counts(pod)
        )
        ready, total = ready_containers(pod)

        missing_requests += pod_missing_requests
        missing_limits += pod_missing_limits
        not_ready += 1 if total and ready < total else 0

    return {
        "phases": phases,
        "restarts": restarts,
        "oom": oom_count,
        "crash_looping": crash_looping,
        "missing_requests": missing_requests,
        "missing_limits": missing_limits,
        "not_ready": not_ready
    }


def score_namespace(deployment_reports, pod_report):
    risk = RiskEngine()
    recommendations = RecommendationEngine()

    pending = pod_report["phases"].get("Pending", 0)
    failed = pod_report["phases"].get("Failed", 0)

    risk.penalize(pending * 5, "Pending pods detected")
    risk.penalize(failed * 10, "Failed pods detected")
    risk.penalize(
        min(pod_report["restarts"], 30),
        "Restart activity detected"
    )
    risk.penalize(
        pod_report["oom"] * 10,
        "OOMKilled events detected"
    )
    risk.penalize(
        pod_report["crash_looping"] * 20,
        "CrashLoopBackOff pods detected"
    )
    risk.penalize(
        min(
            (
                pod_report["missing_requests"]
                + pod_report["missing_limits"]
            ) * 2,
            20
        ),
        "Resource governance gaps detected"
    )

    recommendations.add(
        pod_report["restarts"] > 0,
        "Inspect top restarting deployments and recent rollout changes."
    )
    recommendations.add(
        pod_report["oom"] > 0,
        "Review memory limits, memory requests, and recent memory usage."
    )
    recommendations.add(
        pod_report["crash_looping"] > 0,
        "Check CrashLoopBackOff pod logs and startup dependencies."
    )
    recommendations.add(
        pod_report["missing_requests"] > 0,
        "Add CPU and memory requests to application containers."
    )
    recommendations.add(
        pod_report["missing_limits"] > 0,
        "Add CPU and memory limits for predictable failure behavior."
    )
    recommendations.add(
        any(report["ready"] < report["desired"] for report in deployment_reports),
        "Prioritize deployments with unavailable replicas."
    )

    result = risk.result()
    result["recommendations"] = recommendations.items()

    return result


def print_namespace_summary(
    namespace,
    deployments,
    pods,
    summary,
    pod_report
):
    score = summary["score"]
    table = Table(
        title=f"Namespace Investigation ({namespace})"
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Health Score", f"[{score_style(score)}]{score}/100")
    table.add_row("Risk", risk_from_score(score))
    table.add_row("Deployments", str(len(deployments)))
    table.add_row("Pods", str(len(pods)))
    table.add_row("Restarts", str(pod_report["restarts"]))
    table.add_row("OOM Events", str(pod_report["oom"]))
    table.add_row(
        "CrashLoopBackOff Pods",
        str(pod_report["crash_looping"])
    )
    table.add_row(
        "Missing Requests",
        str(pod_report["missing_requests"])
    )
    table.add_row(
        "Missing Limits",
        str(pod_report["missing_limits"])
    )

    console.print(table)


def print_deployment_inventory(reports):
    table = Table(title="Deployment Inventory")
    table.add_column("Deployment")
    table.add_column("Ready")
    table.add_column("Pods")
    table.add_column("Restarts")
    table.add_column("OOM")
    table.add_column("Score")
    table.add_column("Risk")

    for report in sorted(reports, key=lambda item: item["score"]):
        score = report["score"]
        table.add_row(
            report["name"],
            f"{report['ready']}/{report['desired']}",
            str(report["pods"]),
            str(report["restarts"]),
            str(report["oom"]),
            f"[{score_style(score)}]{score}[/]",
            report["risk"]
        )

    console.print()
    console.print(table)


def print_pod_inventory(pods):
    table = Table(title="Pod Inventory")
    table.add_column("Pod")
    table.add_column("Phase")
    table.add_column("Ready")
    table.add_column("Restarts")
    table.add_column("Node")

    for pod in sorted(pods, key=lambda item: item.metadata.name):
        ready, total = ready_containers(pod)
        table.add_row(
            pod.metadata.name,
            str(pod.status.phase),
            f"{ready}/{total}",
            str(total_restarts(pod)),
            str(pod.spec.node_name or "-")
        )

    console.print()
    console.print(table)


def print_restart_hotspots(reports):
    hotspots = [
        report for report in reports
        if report["restarts"] > 0
    ]
    hotspots.sort(
        key=lambda item: item["restarts"],
        reverse=True
    )

    console.print()
    console.print("[bold yellow]Top Restarting Deployments[/bold yellow]")

    if not hotspots:
        console.print("[green]No restart hotspots detected[/green]")
        return

    for report in hotspots[:5]:
        console.print(
            f"- {report['name']}: {report['restarts']} restarts"
        )


def print_oom_hotspots(reports):
    hotspots = [
        report for report in reports
        if report["oom"] > 0
    ]
    hotspots.sort(
        key=lambda item: item["oom"],
        reverse=True
    )

    console.print()
    console.print("[bold yellow]OOM Events[/bold yellow]")

    if not hotspots:
        console.print("[green]No OOM events detected[/green]")
        return

    for report in hotspots[:5]:
        console.print(
            f"- {report['name']}: {report['oom']} OOM events"
        )


def print_top_problematic_workloads(reports):
    console.print()
    console.print("[bold red]Top Problematic Workloads[/bold red]")

    problematic = [
        report for report in reports
        if report["score"] < 90
    ]
    problematic.sort(key=lambda item: item["score"])

    if not problematic:
        console.print("[green]No problematic workloads detected[/green]")
        return

    for report in problematic[:5]:
        reasons = ", ".join(report["reasons"][:2])
        console.print(
            f"- {report['name']}: {report['score']}/100 ({reasons})"
        )


def print_recommendations(recommendations):
    console.print()
    console.print("[bold cyan]Recommendations[/bold cyan]")

    if not recommendations:
        console.print("[green]No recommendations[/green]")
        return

    for item in recommendations:
        console.print(f"- {item}")
