from collections import defaultdict
from typing import Optional

from rich.table import Table

from kdoctor.clients.kube_client import get_core_v1
from kdoctor.utils.output import console, render


def analyze_cluster(details: bool = False, output_format: Optional[str] = None):

    v1 = get_core_v1()

    node_stats = analyze_nodes(v1, quiet=bool(output_format))
    pod_stats = analyze_pods(v1, quiet=bool(output_format))
    system_components = analyze_system_components(v1, quiet=bool(output_format))

    score = calculate_cluster_score(
        node_stats["not_ready"], pod_stats["pending"], pod_stats["failed"]
    )

    result = {
        "cluster_score": score,
        "risk": get_risk(score),
        "nodes": node_stats,
        "pods": pod_stats,
        "system_components": system_components,
    }

    if details:
        result["top_namespaces"] = collect_top_namespaces(v1)
        result["top_nodes"] = collect_top_nodes(v1)

    if output_format and render(result, output_format):
        return

    console.print()

    console.print(f"[bold blue]Cluster Score:[/bold blue] {score}/100")

    console.print(f"[bold blue]Risk:[/bold blue] {get_risk(score)}")

    if details:

        console.print()

        analyze_top_namespaces(v1)

        console.print()

        analyze_top_nodes(v1)


def analyze_nodes(v1, quiet: bool = False):

    nodes = v1.list_node()

    ready_nodes = 0
    not_ready_nodes = 0
    unschedulable_nodes = 0

    memory_pressure = 0
    disk_pressure = 0
    pid_pressure = 0

    for node in nodes.items:

        if node.spec.unschedulable:
            unschedulable_nodes += 1

        for condition in node.status.conditions:

            if condition.type == "Ready":

                if condition.status == "True":
                    ready_nodes += 1
                else:
                    not_ready_nodes += 1

            elif condition.type == "MemoryPressure" and condition.status == "True":
                memory_pressure += 1

            elif condition.type == "DiskPressure" and condition.status == "True":
                disk_pressure += 1

            elif condition.type == "PIDPressure" and condition.status == "True":
                pid_pressure += 1

    if not quiet:
        table = Table(title="Node Health")

        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Ready Nodes", str(ready_nodes))

        table.add_row("NotReady Nodes", str(not_ready_nodes))

        table.add_row("Unschedulable Nodes", str(unschedulable_nodes))

        table.add_row("Memory Pressure", str(memory_pressure))

        table.add_row("Disk Pressure", str(disk_pressure))

        table.add_row("PID Pressure", str(pid_pressure))

        console.print(table)

    return {
        "ready": ready_nodes,
        "not_ready": not_ready_nodes,
        "unschedulable": unschedulable_nodes,
        "memory_pressure": memory_pressure,
        "disk_pressure": disk_pressure,
        "pid_pressure": pid_pressure,
    }


def analyze_pods(v1, quiet: bool = False):

    pods = v1.list_pod_for_all_namespaces()

    running = 0
    pending = 0
    failed = 0
    succeeded = 0

    pending_pods = []
    pending_reasons = []

    for pod in pods.items:

        phase = pod.status.phase

        if phase == "Running":

            running += 1

        elif phase == "Pending":

            pending += 1

            pending_pods.append(f"{pod.metadata.namespace}/{pod.metadata.name}")

            conditions = pod.status.conditions or []

            for condition in conditions:

                if condition.type == "PodScheduled" and condition.status == "False":

                    pending_reasons.append((pod.metadata.name, condition.message))

        elif phase == "Failed":

            failed += 1

        elif phase == "Succeeded":

            succeeded += 1

    if not quiet:
        table = Table(title="Pod Summary")

        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Running", str(running))

        table.add_row("Pending", str(pending))

        table.add_row("Failed", str(failed))

        table.add_row("Succeeded", str(succeeded))

        console.print(table)

        if pending_pods:

            console.print()
            console.print("[bold yellow]Pending Pods[/bold yellow]")

            for pod in pending_pods[:20]:

                console.print(f"⚠ {pod}")

        if pending_reasons:

            console.print()
            console.print("[bold yellow]Pending Reasons[/bold yellow]")

            for pod_name, reason in pending_reasons[:10]:

                console.print(f"⚠ {pod_name}: {reason}")

    return {
        "running": running,
        "pending": pending,
        "failed": failed,
        "succeeded": succeeded,
        "pending_pods": pending_pods,
        "pending_reasons": [
            {"pod": pod_name, "message": reason} for pod_name, reason in pending_reasons
        ],
    }


def analyze_system_components(v1, quiet: bool = False):

    coredns = False
    metrics_server = False

    try:

        pods = v1.list_namespaced_pod(namespace="kube-system")

        for pod in pods.items:

            name = pod.metadata.name

            if "coredns" in name:
                coredns = True

            if "metrics-server" in name:
                metrics_server = True

        if not quiet:
            table = Table(title="System Components")

            table.add_column("Component")
            table.add_column("Status")

            table.add_row("CoreDNS", "Healthy" if coredns else "Missing")

            table.add_row("Metrics Server", "Healthy" if metrics_server else "Missing")

            console.print(table)

        return {"coredns": coredns, "metrics_server": metrics_server}

    except Exception as e:

        console.print(f"[red]Failed to check kube-system:[/red] {e}")
        return {"coredns": coredns, "metrics_server": metrics_server, "error": str(e)}


def calculate_cluster_score(not_ready_nodes, pending_pods, failed_pods):

    score = 100

    score -= not_ready_nodes * 10

    score -= pending_pods * 2

    score -= failed_pods * 5

    return max(0, score)


def get_risk(score):

    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"


def collect_top_namespaces(v1):

    pods = v1.list_pod_for_all_namespaces()

    counts = defaultdict(int)

    for pod in pods.items:

        counts[pod.metadata.namespace] += 1

    return [
        {"namespace": ns, "pods": count}
        for ns, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]


def analyze_top_namespaces(v1, quiet: bool = False):

    results = collect_top_namespaces(v1)

    if quiet:
        return results

    table = Table(title="Top Namespaces By Pod Count")

    table.add_column("Namespace")
    table.add_column("Pods")

    for item in results:

        table.add_row(item["namespace"], str(item["pods"]))

    console.print(table)


def collect_top_nodes(v1):

    pods = v1.list_pod_for_all_namespaces()

    counts = defaultdict(int)

    for pod in pods.items:

        if pod.spec.node_name:

            counts[pod.spec.node_name] += 1

    return [
        {"node": node, "pods": count}
        for node, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]


def analyze_top_nodes(v1, quiet: bool = False):

    results = collect_top_nodes(v1)

    if quiet:
        return results

    table = Table(title="Top Nodes By Pod Count")

    table.add_column("Node")
    table.add_column("Pods")

    for item in results:

        table.add_row(item["node"], str(item["pods"]))

    console.print(table)


def analyze_hotspots(output_format: str = None):
    v1 = get_core_v1()

    restart_hotspots = collect_restart_hotspots(v1)
    namespace_hotspots = collect_namespace_hotspots(v1)
    node_hotspots = collect_node_hotspots(v1)

    if output_format and render(
        {
            "restart_hotspots": restart_hotspots,
            "namespace_hotspots": namespace_hotspots,
            "node_hotspots": node_hotspots,
        },
        output_format,
    ):
        return

    find_restart_hotspots_display(restart_hotspots)
    find_namespace_hotspots_display(namespace_hotspots)
    find_node_hotspots_display(node_hotspots)


def collect_restart_hotspots(v1):
    pods = v1.list_pod_for_all_namespaces()

    restarts = []

    for pod in pods.items:

        total_restarts = 0

        for cs in pod.status.container_statuses or []:
            total_restarts += cs.restart_count

        if total_restarts > 0:

            restarts.append(
                {
                    "pod": f"{pod.metadata.namespace}/{pod.metadata.name}",
                    "restarts": total_restarts,
                }
            )

    restarts.sort(key=lambda x: x["restarts"], reverse=True)

    return restarts[:10]


def find_restart_hotspots(v1):
    restart_hotspots = collect_restart_hotspots(v1)
    find_restart_hotspots_display(restart_hotspots)


def find_restart_hotspots_display(restarts):

    table = Table(title="Top Restarting Pods")

    table.add_column("Pod")
    table.add_column("Restarts")

    for item in restarts:

        table.add_row(item["pod"], str(item["restarts"]))

    console.print()
    console.print(table)


def collect_namespace_hotspots(v1):
    pods = v1.list_pod_for_all_namespaces()

    namespace_counts = {}

    for pod in pods.items:

        namespace = pod.metadata.namespace

        namespace_counts[namespace] = namespace_counts.get(namespace, 0) + 1

    return [
        {"namespace": ns, "pods": count}
        for ns, count in sorted(
            namespace_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
    ]


def find_namespace_hotspots(v1):
    hotspots = collect_namespace_hotspots(v1)
    find_namespace_hotspots_display(hotspots)


def find_namespace_hotspots_display(hotspots):

    table = Table(title="Top Namespaces")

    table.add_column("Namespace")
    table.add_column("Pods")

    for item in hotspots:

        table.add_row(item["namespace"], str(item["pods"]))

    console.print()
    console.print(table)


def collect_node_hotspots(v1):
    pods = v1.list_pod_for_all_namespaces()

    node_counts = {}

    for pod in pods.items:

        node = pod.spec.node_name

        if not node:
            continue

        node_counts[node] = node_counts.get(node, 0) + 1

    sorted_nodes = sorted(node_counts.items(), key=lambda x: x[1], reverse=True)

    result = [{"node": node, "pods": count} for node, count in sorted_nodes[:10]]

    if len(sorted_nodes) > 1:

        highest = sorted_nodes[0][1]
        lowest = sorted_nodes[-1][1]

        spread = highest - lowest

        result.append({"imbalance_warning": spread > 20, "spread": spread})

    return result


def find_node_hotspots(v1):
    node_hotspots = collect_node_hotspots(v1)
    find_node_hotspots_display(node_hotspots)


def find_node_hotspots_display(node_hotspots):

    table = Table(title="Node Distribution")

    table.add_column("Node")
    table.add_column("Pods")

    for item in [h for h in node_hotspots if "node" in h]:

        table.add_row(item["node"], str(item["pods"]))

    console.print()
    console.print(table)

    imbalance_item = [h for h in node_hotspots if "imbalance_warning" in h]

    if imbalance_item:

        spread = imbalance_item[0]["spread"]
        console.print()

        if imbalance_item[0]["imbalance_warning"]:

            console.print(
                f"[yellow]Node imbalance detected. Spread: {spread} pods[/yellow]"
            )

        else:

            console.print(
                f"[green]Node distribution healthy. Spread: {spread} pods[/green]"
            )
