from rich.console import Console
from rich.table import Table

from kdoctor.clients.kube_client import get_core_v1
from kdoctor.analyzers.pod_analyzer import calculate_health_score

console = Console()


def analyze_namespace(namespace):

    v1 = get_core_v1()

    pods = v1.list_namespaced_pod(
        namespace=namespace
    )

    total = 0
    running = 0
    pending = 0
    failed = 0

    score_total = 0

    missing_requests = 0
    missing_limits = 0
    restarting = 0
    not_ready = 0

    for pod in pods.items:

        total += 1

        if pod.status.phase == "Running":
            running += 1

        elif pod.status.phase == "Pending":
            pending += 1

        elif pod.status.phase == "Failed":
            failed += 1

        score, recommendations = calculate_health_score(
            pod
        )

        score_total += score

        for recommendation in recommendations:

            text = recommendation.lower()

            if "requests" in text:
                missing_requests += 1

            if "limits" in text:
                missing_limits += 1

            if "restart" in text:
                restarting += 1

            if "not ready" in text:
                not_ready += 1

    avg_score = (
        int(score_total / total)
        if total > 0
        else 0
    )

    table = Table(
        title=f"Namespace Report ({namespace})"
    )

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Total Pods", str(total))
    table.add_row("Running", str(running))
    table.add_row("Pending", str(pending))
    table.add_row("Failed", str(failed))
    table.add_row("Health Score", str(avg_score))
    table.add_row("Risk", get_risk(avg_score))

    console.print(table)

    console.print()

    console.print("[bold yellow]Top Issues[/bold yellow]")

    console.print(
        f"⚠ Missing Requests: {missing_requests}"
    )

    console.print(
        f"⚠ Missing Limits: {missing_limits}"
    )

    console.print(
        f"⚠ Restarting Pods: {restarting}"
    )

    console.print(
        f"⚠ Not Ready Pods: {not_ready}"
    )

def get_risk(score):

    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"

