from rich.table import Table
from typing import Optional

from kdoctor.analyzers.pod_analyzer import calculate_health_score
from kdoctor.clients.kube_client import get_apps_v1, get_core_v1
from kdoctor.utils.output import console, render


def analyze_deployment(
    deployment_name,
    namespace,
    output_format: Optional[str] = None
):

    apps = get_apps_v1()
    core = get_core_v1()

    deployment = apps.read_namespaced_deployment(
        deployment_name,
        namespace
    )

    selector = deployment.spec.selector.match_labels

    selector_string = ",".join(
        [
            f"{k}={v}"
            for k, v in selector.items()
        ]
    )

    pods = core.list_namespaced_pod(
        namespace,
        label_selector=selector_string
    )

    score = 100

    desired = deployment.spec.replicas
    available = deployment.status.available_replicas or 0
    ready = deployment.status.ready_replicas or 0

    if available < desired:
        score -= 20

    if ready < desired:
        score -= 10

    pod_scores = []

    for pod in pods.items:

        pod_score, _ = calculate_health_score(
            pod
        )

        pod_scores.append(
            pod_score
        )

    avg_score = (
        sum(pod_scores) // len(pod_scores)
        if pod_scores
        else 0
    )

    final_score = (
        score + avg_score
    ) // 2

    output_data = {
        "deployment": deployment_name,
        "namespace": namespace,
        "desired_replicas": desired,
        "available_replicas": available,
        "ready_replicas": ready,
        "deployment_health_score": score,
        "average_pod_score": avg_score,
        "final_health_score": final_score,
        "risk": get_risk(final_score),
        "pod_count": len(pods.items)
    }

    if output_format and render(output_data, output_format):
        return

    table = Table(
        title="Deployment Analysis"
    )

    table.add_column("Field")
    table.add_column("Value")

    table.add_row(
        "Deployment",
        deployment_name
    )

    table.add_row(
        "Namespace",
        namespace
    )

    table.add_row(
        "Desired Replicas",
        str(desired)
    )

    table.add_row(
        "Available Replicas",
        str(available)
    )

    table.add_row(
        "Ready Replicas",
        str(ready)
    )

    console.print(table)

    console.print()

    console.print(
        f"Health Score: {final_score}"
    )

    console.print(
        f"Risk: {get_risk(final_score)}"
    )


def analyze_all_deployments(
    namespace,
    output_format: Optional[str] = None
):
    apps = get_apps_v1()

    deployments = apps.list_namespaced_deployment(
        namespace
    )

    results = []

    for deployment in deployments.items:

        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        available = deployment.status.available_replicas or 0

        score = 100

        if ready < desired:
            score -= 20

        if available < desired:
            score -= 10

        score = max(score, 0)

        results.append(
            {
                "name": deployment.metadata.name,
                "ready": f"{ready}/{desired}",
                "ready_count": ready,
                "desired_count": desired,
                "available_count": available,
                "score": score,
                "risk": get_risk(score)
            }
        )

    results.sort(
        key=lambda x: x["score"]
    )

    if output_format and render(
        {
            "namespace": namespace,
            "deployments": results,
            "summary": calculate_deployment_summary(results)
        },
        output_format
    ):
        return

    table = Table(
        title=f"Deployment Health Report ({namespace})"
    )

    table.add_column("Deployment")
    table.add_column("Ready")
    table.add_column("Score")
    table.add_column("Risk")

    for item in results:

        table.add_row(
            item["name"],
            item["ready"],
            str(item["score"]),
            item["risk"]
        )

    console.print(table)


def calculate_deployment_summary(results):
    return {
        "total": len(results),
        "healthy": len([r for r in results if r["score"] >= 90]),
        "warning": len([r for r in results if 70 <= r["score"] < 90]),
        "critical": len([r for r in results if r["score"] < 70])
    }

def get_risk(score):

    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"

