from rich.console import Console
from rich.table import Table

from kubernetes import client
from kubernetes import config

from kdoctor.analyzers.pod_analyzer import calculate_health_score

console = Console()


def analyze_deployment(
    deployment_name,
    namespace
):

    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    apps = client.AppsV1Api()
    core = client.CoreV1Api()

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

    console.print()

    console.print(
        f"Health Score: {final_score}"
    )

    console.print(
        f"Risk: {get_risk(final_score)}"
    )

def analyze_all_deployments(namespace):

    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    apps = client.AppsV1Api()

    deployments = apps.list_namespaced_deployment(
        namespace
    )

    table = Table(
        title=f"Deployment Health Report ({namespace})"
    )

    table.add_column("Deployment")
    table.add_column("Ready")
    table.add_column("Score")
    table.add_column("Risk")

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
                "score": score,
                "risk": get_risk(score)
            }
        )

    results.sort(
        key=lambda x: x["score"]
    )

    for item in results:

        table.add_row(
            item["name"],
            item["ready"],
            str(item["score"]),
            item["risk"]
        )

    console.print(table)

def get_risk(score):

    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"

