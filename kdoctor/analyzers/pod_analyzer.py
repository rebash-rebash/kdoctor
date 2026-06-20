from rich.console import Console
from rich.table import Table

from kdoctor.clients.kube_client import get_core_v1
from kdoctor.utils.output import render

console = Console()

SYSTEM_CONTAINERS = {
    "istio-proxy",
    "linkerd-proxy"
}


def analyze_pod(
    pod_name: str,
    namespace: str,
    output_format: str = None
):
    v1 = get_core_v1()

    try:
        pod = v1.read_namespaced_pod(
            name=pod_name,
            namespace=namespace
        )
    except Exception as e:
        console.print(
            f"[red]Failed to fetch pod:[/red] {e}"
        )
        return

    score, recommendations = calculate_health_score(pod)
    container_data = get_container_data(pod)
    events = collect_events(v1, pod_name, namespace)

    output_data = {
        "pod_name": pod.metadata.name,
        "namespace": namespace,
        "status": str(pod.status.phase),
        "node": str(pod.spec.node_name),
        "pod_ip": str(pod.status.pod_ip),
        "health_score": score,
        "grade": get_grade(score),
        "recommendations": recommendations,
        "containers": container_data,
        "events": events
    }

    if output_format and render(output_data, output_format):
        return

    print_pod_summary(pod, namespace)
    print_container_table(pod)

    console.print()
    console.print(
        f"[bold blue]Health Score:[/bold blue] {score}/100"
    )

    console.print(
        f"[bold blue]Grade:[/bold blue] {get_grade(score)}"
    )

    console.print()

    if recommendations:
        console.print(
            "[bold yellow]Recommendations[/bold yellow]"
        )

        for item in recommendations:
            console.print(f"⚠ {item}")
    else:
        console.print(
            "[green]✓ No issues found[/green]"
        )

    print_events(
        v1,
        pod_name,
        namespace
    )


def print_pod_summary(pod, namespace):

    table = Table(title="Pod Analysis")

    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row(
        "Pod Name",
        pod.metadata.name
    )

    table.add_row(
        "Namespace",
        namespace
    )

    table.add_row(
        "Status",
        str(pod.status.phase)
    )

    table.add_row(
        "Node",
        str(pod.spec.node_name)
    )

    table.add_row(
        "Pod IP",
        str(pod.status.pod_ip)
    )

    console.print(table)


def get_container_data(pod):
    statuses = {
        cs.name: cs
        for cs in (
            pod.status.container_statuses or []
        )
    }

    containers = []

    for container in pod.spec.containers:
        status = statuses.get(container.name)
        containers.append(
            {
                "name": container.name,
                "ready": bool(status and status.ready),
                "restarts": int(status.restart_count) if status else 0,
                "resources": {
                    "requests": getattr(container.resources, "requests", None),
                    "limits": getattr(container.resources, "limits", None)
                }
            }
        )

    return containers


def collect_events(v1, pod_name, namespace):
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=(
                f"involvedObject.name={pod_name}"
            )
        )

        sorted_events = sorted(
            events.items,
            key=lambda e: (
                e.last_timestamp
                or e.event_time
                or e.metadata.creation_timestamp
            ),
            reverse=True
        )

        return [
            {
                "reason": event.reason,
                "message": event.message,
                "type": event.type,
                "timestamp": str(
                    event.last_timestamp
                    or event.event_time
                    or event.metadata.creation_timestamp
                )
            }
            for event in sorted_events[:10]
        ]
    except Exception:
        return []


def print_container_table(pod):

    statuses = {
        cs.name: cs
        for cs in (
            pod.status.container_statuses or []
        )
    }

    table = Table(title="Containers")

    table.add_column("Container")
    table.add_column("Ready")
    table.add_column("Restarts")

    for container in pod.spec.containers:

        status = statuses.get(
            container.name
        )

        ready = (
            "✓"
            if status and status.ready
            else "✗"
        )

        restarts = (
            str(status.restart_count)
            if status
            else "0"
        )

        table.add_row(
            container.name,
            ready,
            restarts
        )

    console.print()
    console.print(table)


def calculate_health_score(pod):

    score = 100

    recommendations = []

    statuses = {
        cs.name: cs
        for cs in (
            pod.status.container_statuses or []
        )
    }

    for container in pod.spec.containers:

        is_system_container = (
            container.name
            in SYSTEM_CONTAINERS
        )

        status = statuses.get(
            container.name
        )

        if status:

            if not status.ready:
                score -= 15

                recommendations.append(
                    f"{container.name}: Container not ready"
                )

            if status.restart_count > 0:
                score -= 5

                recommendations.append(
                    f"{container.name}: Restart count = {status.restart_count}"
                )

            if status.restart_count > 5:
                score -= 10

                recommendations.append(
                    f"{container.name}: High restart count"
                )

            waiting = getattr(
                status.state,
                "waiting",
                None
            )

            if waiting:
                score -= 20

                recommendations.append(
                    f"{container.name}: {waiting.reason}"
                )

        if is_system_container:
            continue

        resources = container.resources

        requests = (
            resources.requests
            if resources
            else None
        )

        limits = (
            resources.limits
            if resources
            else None
        )

        if not requests:
            score -= 10

            recommendations.append(
                f"{container.name}: Missing resource requests"
            )

        if not limits:
            score -= 10

            recommendations.append(
                f"{container.name}: Missing resource limits"
            )

        if not container.liveness_probe:
            score -= 5

            recommendations.append(
                f"{container.name}: Missing liveness probe"
            )

        if not container.readiness_probe:
            score -= 5

            recommendations.append(
                f"{container.name}: Missing readiness probe"
            )

        if not container.security_context:
            score -= 5

            recommendations.append(
                f"{container.name}: Missing security context"
            )

    score = max(
        0,
        min(score, 100)
    )

    return score, recommendations


def get_grade(score):

    if score >= 95:
        return "A+"

    if score >= 90:
        return "A"

    if score >= 80:
        return "B"

    if score >= 70:
        return "C"

    if score >= 60:
        return "D"

    return "F"


def print_events(
    v1,
    pod_name,
    namespace
):

    try:

        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=(
                f"involvedObject.name={pod_name}"
            )
        )

        if not events.items:
            return

        console.print()
        console.print(
            "[bold cyan]Recent Events[/bold cyan]"
        )

        sorted_events = sorted(
            events.items,
            key=lambda e: (
                e.last_timestamp
                or e.event_time
                or e.metadata.creation_timestamp
            ),
            reverse=True
        )

        for event in sorted_events[:10]:

            console.print(
                f"[yellow]{event.reason}[/yellow] - "
                f"{event.message}"
            )

    except Exception as e:

        console.print(
            f"[red]Unable to fetch events:[/red] {e}"
        )

def analyze_all_pods(
    namespace: str,
    critical_only: bool = False,
    warning_only: bool = False,
    top: int = 0,
    output_format: str = None
):

    v1 = get_core_v1()

    try:
        pods = v1.list_namespaced_pod(
            namespace=namespace
        )

    except Exception as e:

        console.print(
            f"[red]Failed to fetch pods:[/red] {e}"
        )

        return

    if not pods.items:

        console.print(
            f"[yellow]No pods found in namespace {namespace}[/yellow]"
        )

        return

    pod_results = []

    for pod in pods.items:

        score, _ = calculate_health_score(
            pod
        )

        ready_count = 0
        total_count = 0
        restarts = 0

        for cs in (
            pod.status.container_statuses or []
        ):

            total_count += 1

            if cs.ready:
                ready_count += 1

            restarts += cs.restart_count

        pod_results.append(
            {
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ready": f"{ready_count}/{total_count}",
                "ready_count": ready_count,
                "total_count": total_count,
                "restarts": restarts,
                "score": score,
                "risk": get_risk(score),
                "grade": get_grade(score)
            }
        )

    # lowest score first
    pod_results.sort(
        key=lambda p: p["score"]
    )

    if critical_only:

        pod_results = [
            p for p in pod_results
            if p["score"] < 70
        ]

    if warning_only:

        pod_results = [
            p for p in pod_results
            if 70 <= p["score"] < 90
        ]

    if top > 0:

        pod_results = pod_results[:top]

    if output_format and render(
        {
            "namespace": namespace,
            "pods": pod_results,
            "summary": calculate_pod_summary(pod_results)
        },
        output_format
    ):
        return

    table = Table(
        title=f"Pod Health Report ({namespace})"
    )

    table.add_column("Pod")
    table.add_column("Status")
    table.add_column("Ready")
    table.add_column("Restarts")
    table.add_column("Score")
    table.add_column("Risk")
    table.add_column("Grade")

    for pod in pod_results:

        score_style = get_score_style(
            pod["score"]
        )

        table.add_row(
            pod["name"],
            pod["status"],
            pod["ready"],
            str(pod["restarts"]),
            f"[{score_style}]{pod['score']}[/{score_style}]",
            pod["risk"],
            pod["grade"]
        )

    console.print(table)

    print_summary(
        pod_results
    )


def calculate_pod_summary(pod_results):
    total = len(pod_results)

    healthy = len(
        [
            p for p in pod_results
            if p["score"] >= 90
        ]
    )

    warning = len(
        [
            p for p in pod_results
            if 70 <= p["score"] < 90
        ]
    )

    critical = len(
        [
            p for p in pod_results
            if p["score"] < 70
        ]
    )

    return {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical
    }


def get_risk(score):

    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"

def get_score_style(score):

    if score >= 90:
        return "green"

    if score >= 70:
        return "yellow"

    return "red"

def print_summary(results):

    total = len(results)

    healthy = len(
        [
            p for p in results
            if p["score"] >= 90
        ]
    )

    warning = len(
        [
            p for p in results
            if 70 <= p["score"] < 90
        ]
    )

    critical = len(
        [
            p for p in results
            if p["score"] < 70
        ]
    )

    console.print()

    console.print(
        f"[green]Healthy:[/green] {healthy}"
    )

    console.print(
        f"[yellow]Warning:[/yellow] {warning}"
    )

    console.print(
        f"[red]Critical:[/red] {critical}"
    )

    console.print(
        f"[blue]Total:[/blue] {total}"
    )