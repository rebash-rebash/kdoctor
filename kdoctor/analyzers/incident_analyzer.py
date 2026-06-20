from rich.console import Console
from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1, get_core_v1
from kdoctor.utils.kube import (
    oom_events,
    revision_label,
    revision_number,
    total_restarts
)

console = Console()


def investigate_incident(timeout: int = 15):
    try:
        core = get_core_v1()
        apps = get_apps_v1()
        pods = core.list_pod_for_all_namespaces(
            _request_timeout=timeout
        ).items
        nodes = core.list_node(
            _request_timeout=timeout
        ).items
        deployments = apps.list_deployment_for_all_namespaces(
            _request_timeout=timeout
        ).items
        replicasets = list_replicasets(apps, timeout)
    except Exception as e:
        console.print(
            f"[red]Failed to investigate incident:[/red] {e}"
        )
        return

    pod_summary = analyze_cluster_pods(pods)
    node_issues = analyze_node_issues(nodes)
    deployment_summary = analyze_deployments(
        deployments,
        pods,
        replicasets
    )
    likely_cause = choose_likely_cause(
        pod_summary,
        node_issues,
        deployment_summary
    )

    print_incident_summary(
        likely_cause,
        pod_summary,
        node_issues,
        deployment_summary
    )


def analyze_cluster_pods(pods):
    pending = []
    failed = []
    restarting = []
    oom = []

    for pod in pods:
        name = f"{pod.metadata.namespace}/{pod.metadata.name}"

        if pod.status.phase == "Pending":
            pending.append(name)

        if pod.status.phase == "Failed":
            failed.append(name)

        restarts = total_restarts(pod)
        if restarts:
            restarting.append((name, restarts))

        oom_count = oom_events(pod)
        if oom_count:
            oom.append((name, oom_count))

    restarting.sort(key=lambda item: item[1], reverse=True)
    oom.sort(key=lambda item: item[1], reverse=True)

    return {
        "pending": pending,
        "failed": failed,
        "restarting": restarting,
        "oom": oom
    }


def analyze_node_issues(nodes):
    issues = []

    for node in nodes:
        for condition in node.status.conditions or []:
            if (
                condition.type == "Ready"
                and condition.status != "True"
            ):
                issues.append(
                    (node.metadata.name, "NotReady")
                )

            if (
                condition.type in [
                    "MemoryPressure",
                    "DiskPressure",
                    "PIDPressure"
                ]
                and condition.status == "True"
            ):
                issues.append(
                    (node.metadata.name, condition.type)
                )

    return issues


def list_replicasets(apps, timeout):
    try:
        return apps.list_replica_set_for_all_namespaces(
            _request_timeout=timeout
        ).items
    except Exception:
        return []


def analyze_deployments(deployments, all_pods, all_replicasets):
    reports = []
    pods_by_namespace = group_by_namespace(all_pods)
    replicasets_by_deployment_uid = group_replicasets_by_owner(
        all_replicasets
    )

    for deployment in deployments:
        namespace = deployment.metadata.namespace
        pods = matching_deployment_pods(
            deployment,
            pods_by_namespace.get(namespace, [])
        )
        replicasets = replicasets_by_deployment_uid.get(
            deployment.metadata.uid,
            []
        )
        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        restarts = sum(total_restarts(pod) for pod in pods)
        ooms = sum(oom_events(pod) for pod in pods)

        if ready >= desired and restarts == 0 and ooms == 0:
            continue

        reports.append(
            {
                "name": (
                    f"{namespace}/{deployment.metadata.name}"
                ),
                "desired": desired,
                "ready": ready,
                "restarts": restarts,
                "oom": ooms,
                "revision": (
                    revision_label(replicasets[0])
                    if replicasets else "?"
                )
            }
        )

    reports.sort(
        key=lambda item: (
            item["restarts"] + item["oom"] * 5
            + max(0, item["desired"] - item["ready"]) * 10
        ),
        reverse=True
    )

    return reports


def group_by_namespace(resources):
    grouped = {}

    for resource in resources:
        namespace = resource.metadata.namespace
        grouped.setdefault(namespace, []).append(resource)

    return grouped


def group_replicasets_by_owner(replicasets):
    grouped = {}

    for replicaset in replicasets:
        for owner in replicaset.metadata.owner_references or []:
            grouped.setdefault(owner.uid, []).append(replicaset)

    for owned_replicasets in grouped.values():
        owned_replicasets.sort(
            key=lambda item: revision_number(item),
            reverse=True
        )

    return grouped


def matching_deployment_pods(deployment, pods):
    selector = deployment.spec.selector.match_labels or {}

    if not selector:
        return []

    return [
        pod for pod in pods
        if labels_match(selector, pod.metadata.labels or {})
    ]


def labels_match(selector, labels):
    for key, value in selector.items():
        if labels.get(key) != value:
            return False

    return True


def choose_likely_cause(
    pod_summary,
    node_issues,
    deployment_summary
):
    if deployment_summary:
        top = deployment_summary[0]

        if top["restarts"] or top["oom"]:
            return (
                f"Recent rollout or regression in {top['name']} "
                f"revision {top['revision']}"
            )

        return f"Failed deployment {top['name']}"

    if node_issues:
        node, reason = node_issues[0]
        return f"Node issue on {node}: {reason}"

    if pod_summary["pending"]:
        return "Scheduling or capacity issue causing pending pods"

    return "No dominant incident cause detected"


def print_incident_summary(
    likely_cause,
    pod_summary,
    node_issues,
    deployment_summary
):
    console.print("[bold cyan]Incident Summary[/bold cyan]")
    console.print()
    console.print("[bold]Most Likely Cause:[/bold]")
    console.print(likely_cause)

    table = Table(title="Cluster Signals")
    table.add_column("Signal")
    table.add_column("Count")
    table.add_row("Restarting Pods", str(len(pod_summary["restarting"])))
    table.add_row("OOMKilled Pods", str(len(pod_summary["oom"])))
    table.add_row("Pending Pods", str(len(pod_summary["pending"])))
    table.add_row("Failed Pods", str(len(pod_summary["failed"])))
    table.add_row("Node Issues", str(len(node_issues)))
    table.add_row(
        "Failed Deployments",
        str(
            len([
                item for item in deployment_summary
                if item["ready"] < item["desired"]
            ])
        )
    )

    console.print()
    console.print(table)

    print_deployment_evidence(deployment_summary)
    print_pod_evidence(pod_summary)
    print_node_evidence(node_issues)


def print_deployment_evidence(deployment_summary):
    console.print()
    console.print("[bold yellow]Recent Rollouts / Deployments[/bold yellow]")

    if not deployment_summary:
        console.print("[green]No failed deployments detected[/green]")
        return

    table = Table()
    table.add_column("Deployment")
    table.add_column("Ready")
    table.add_column("Revision")
    table.add_column("Restarts")
    table.add_column("OOM")

    for item in deployment_summary[:10]:
        table.add_row(
            item["name"],
            f"{item['ready']}/{item['desired']}",
            item["revision"],
            str(item["restarts"]),
            str(item["oom"])
        )

    console.print(table)


def print_pod_evidence(pod_summary):
    console.print()
    console.print("[bold yellow]Evidence[/bold yellow]")

    for name, restarts in pod_summary["restarting"][:5]:
        console.print(
            f"- Restart count increased: {name} ({restarts})"
        )

    for name, count in pod_summary["oom"][:5]:
        console.print(
            f"- OOMKilled events: {name} ({count})"
        )

    for name in pod_summary["pending"][:5]:
        console.print(f"- Pending pod: {name}")


def print_node_evidence(node_issues):
    if not node_issues:
        return

    console.print()
    console.print("[bold yellow]Node Issues[/bold yellow]")

    for node, reason in node_issues[:10]:
        console.print(f"- {node}: {reason}")
