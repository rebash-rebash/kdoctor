from rich.console import Console
from rich.table import Table

from kubernetes import client
from kubernetes import config
from sympy import python

from kdoctor.analyzers.pod_analyzer import (
    calculate_health_score
)

console = Console()


SYSTEM_CONTAINERS = {
    "istio-proxy",
    "linkerd-proxy"
}


def investigate_deployment(
    deployment_name: str,
    namespace: str,
    deep: bool = False
):

    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

    apps = client.AppsV1Api()
    v1 = client.CoreV1Api()

    try:

        deployment = (
            apps.read_namespaced_deployment(
                deployment_name,
                namespace
            )
        )

    except Exception as e:

        console.print(
            f"[red]Failed to fetch deployment:[/red] {e}"
        )

        return

    selector = (
        deployment.spec.selector.match_labels
    )

    label_selector = ",".join(
        [
            f"{k}={v}"
            for k, v in selector.items()
        ]
    )

    pods = v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=label_selector
    )

    desired = (
        deployment.spec.replicas or 0
    )

    ready = (
        deployment.status.ready_replicas or 0
    )

    updated = (
        deployment.status.updated_replicas or 0
    )

    print_deployment_header(
        deployment_name,
        namespace,
        desired,
        ready,
        updated
    )

    analyze_deployment_pods(
        pods.items,
        deep
    )


def print_deployment_header(
    deployment_name,
    namespace,
    desired,
    ready,
    updated
):

    table = Table(
        title="Deployment Investigation"
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
        "Ready Replicas",
        str(ready)
    )

    table.add_row(
        "Updated Replicas",
        str(updated)
    )

    console.print(table)


def analyze_deployment_pods(
    pods,
    deep=False
):

    if not pods:

        console.print(
            "[yellow]No pods found[/yellow]"
        )

        return

    healthy = 0
    warning = 0
    critical = 0

    operational_score = 100

    pods_missing_requests = set()
    pods_missing_limits = set()

    restarting_pods = 0
    not_ready_pods = 0

    recommendations = []

    worst_pod = None
    highest_restart_count = -1

    for pod in pods:

        statuses = (
            pod.status.container_statuses or []
        )

        pod_has_restart = False
        pod_not_ready = False
        pod_critical = False

        restart_count = 0

        for status in statuses:

            restart_count += (
                status.restart_count
            )

            if status.restart_count > 0:
                pod_has_restart = True

            if not status.ready:
                pod_not_ready = True
                pod_critical = True

            waiting = getattr(
                status.state,
                "waiting",
                None
            )

            if (
                waiting
                and waiting.reason in
                [
                    "CrashLoopBackOff",
                    "ImagePullBackOff",
                    "ErrImagePull",
                    "CreateContainerConfigError"
                ]
            ):
                pod_critical = True

        if restart_count > highest_restart_count:

            highest_restart_count = restart_count
            worst_pod = pod

        if pod_critical:

            critical += 1
            operational_score -= 20

        elif pod_has_restart:

            warning += 1
            operational_score -= 5

        else:

            healthy += 1

        if pod_has_restart:
            restarting_pods += 1

        if pod_not_ready:
            not_ready_pods += 1

        for container in pod.spec.containers:

            if (
                container.name
                in SYSTEM_CONTAINERS
            ):
                continue

            requests = (
                container.resources.requests
                or {}
            )

            limits = (
                container.resources.limits
                or {}
            )

            if not requests:

                pods_missing_requests.add(
                    pod.metadata.name
                )

            if not limits:

                pods_missing_limits.add(
                    pod.metadata.name
                )

    operational_score = max(
        0,
        operational_score
    )

    print_summary(
        len(pods),
        healthy,
        warning,
        critical,
        operational_score
    )

    print_findings(
        len(pods_missing_requests),
        len(pods_missing_limits),
        restarting_pods,
        not_ready_pods
    )

    if len(pods_missing_requests) > 0:

        recommendations.append(
            "Add CPU/Memory requests"
        )

    if len(pods_missing_limits) > 0:

        recommendations.append(
            "Add CPU/Memory limits"
        )

    if restarting_pods > 0:

        recommendations.append(
            "Investigate restart history"
        )

    if recommendations:

        console.print()
        console.print(
            "[bold cyan]Recommendations[/bold cyan]"
        )

        for item in recommendations:

            console.print(
                f"• {item}"
            )

    if worst_pod:

        print_worst_pod(
            worst_pod
        )
    if deep:
        print_deep_analysis(
            pods
        )

def print_summary(
    total,
    healthy,
    warning,
    critical,
    score
):

    table = Table(
        title="Pod Summary"
    )

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row(
        "Total Pods",
        str(total)
    )

    table.add_row(
        "Healthy",
        str(healthy)
    )

    table.add_row(
        "Warning",
        str(warning)
    )

    table.add_row(
        "Critical",
        str(critical)
    )

    table.add_row(
        "Overall Score",
        str(score)
    )

    table.add_row(
        "Risk",
        get_risk(score)
    )

    console.print()
    console.print(table)


def print_findings(
    missing_requests,
    missing_limits,
    restarting_pods,
    not_ready_pods
):

    console.print()
    console.print(
        "[bold yellow]Common Issues[/bold yellow]"
    )

    if missing_requests:
        console.print(
            f"⚠ Missing Resource Requests ({missing_requests})"
        )

    if missing_limits:
        console.print(
            f"⚠ Missing Resource Limits ({missing_limits})"
        )

    if restarting_pods:
        console.print(
            f"⚠ Restarting Pods ({restarting_pods})"
        )

    if not_ready_pods:
        console.print(
            f"⚠ Not Ready Pods ({not_ready_pods})"
        )

    if (
        missing_requests == 0
        and missing_limits == 0
        and restarting_pods == 0
        and not_ready_pods == 0
    ):

        console.print(
            "[green]✓ No issues detected[/green]"
        )


def print_worst_pod(
    pod
):

    console.print()
    console.print(
        "[bold red]Top Problem Pod[/bold red]"
    )

    console.print(
        f"Pod: {pod.metadata.name}"
    )

    for status in (
        pod.status.container_statuses or []
    ):

        if status.restart_count > 0:

            console.print(
                f"Restarts: {status.restart_count}"
            )

            terminated = getattr(
                status.last_state,
                "terminated",
                None
            )

            if terminated:

                console.print(
                    f"Previous Exit Code: {terminated.exit_code}" 
                    )

                console.print(
                    f"Previous Reason: {terminated.reason}" 
                    )
                if terminated.exit_code == 137:
                    console.print( 
                        "[yellow]Possible OOMKill or forced termination[/yellow]" 
                        )


def get_risk(score):

    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"

def print_deep_analysis(
    pods
):

    console.print()
    console.print(
        "[bold cyan]Deep Analysis[/bold cyan]"
    )

    total_restarts = 0

    table = Table(
        title="Pod Details"
    )

    table.add_column("Pod")
    table.add_column("Ready")
    table.add_column("Restarts")
    table.add_column("Status")

    for pod in pods:

        ready = True
        restart_count = 0

        for status in (
            pod.status.container_statuses or []
        ):

            if not status.ready:
                ready = False

            restart_count += (
                status.restart_count
            )

        total_restarts += restart_count

        table.add_row(
            pod.metadata.name,
            "✓" if ready else "✗",
            str(restart_count),
            pod.status.phase
        )

    console.print(table)

    console.print()

    console.print(
        f"Total Restarts: {total_restarts}"
    )

    print_resource_analysis(
        pods
    )

    print_restart_analysis(
        pods
    )

    print_executive_summary(
        pods
    )

def print_resource_analysis(
    pods
):

    console.print()
    console.print(
        "[bold yellow]Resource Analysis[/bold yellow]"
    )

    for pod in pods:

        for container in pod.spec.containers:

            if (
                container.name
                in SYSTEM_CONTAINERS
            ):
                continue

            requests = (
                container.resources.requests
                or {}
            )

            limits = (
                container.resources.limits
                or {}
            )

            if not requests:

                console.print(
                    f"⚠ {pod.metadata.name}: "
                    f"{container.name} missing requests"
                )

            if not limits:

                console.print(
                    f"⚠ {pod.metadata.name}: "
                    f"{container.name} missing limits"
                )
def print_restart_analysis(
    pods
):

    console.print()
    console.print(
        "[bold yellow]Restart Analysis[/bold yellow]"
    )

    for pod in pods:

        for status in (
            pod.status.container_statuses or []
        ):

            if status.restart_count == 0:
                continue

            console.print()

            console.print(
                f"Pod: {pod.metadata.name}"
            )

            console.print(
                f"Container: {status.name}"
            )

            console.print(
                f"Restarts: {status.restart_count}"
            )

            terminated = getattr(
                status.last_state,
                "terminated",
                None
            )

            if terminated:

                console.print(
                    f"Exit Code: {terminated.exit_code}"
                )

                console.print(
                    f"Reason: {terminated.reason}"
                )

                if (
                    terminated.exit_code == 137
                ):

                    console.print(
                        "[red]Possible OOMKill detected[/red]"
                    )

                elif (
                    terminated.exit_code != 0
                ):

                    console.print(
                        "[yellow]Application exited with error[/yellow]"
                    )

def print_executive_summary(pods):

    console.print()
    console.print(
        "[bold green]Executive Summary[/bold green]"
    )

    total_restarts = 0
    oom_events = 0
    app_errors = 0

    for pod in pods:

        for status in (
            pod.status.container_statuses or []
        ):

            total_restarts += (
                status.restart_count
            )

            terminated = getattr(
                status.last_state,
                "terminated",
                None
            )

            if not terminated:
                continue

            if terminated.exit_code == 137:
                oom_events += 1

            elif terminated.exit_code != 0:
                app_errors += 1

    if total_restarts == 0:

        console.print(
            "✓ No restart history detected"
        )

    else:

        console.print(
            f"⚠ Total Restarts: {total_restarts}"
        )

    if oom_events:

        console.print(
            f"⚠ OOM Related Events: {oom_events}"
        )

    if app_errors:

        console.print(
            f"⚠ Application Failures: {app_errors}"
        )