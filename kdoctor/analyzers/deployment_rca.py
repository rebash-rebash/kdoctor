from rich.console import Console
from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1, get_core_v1
from kdoctor.utils.kube import (
    configmap_refs,
    deployment_pods,
    deployment_replicasets,
    is_crash_looping,
    oom_events,
    revision_label,
    secret_refs,
    total_restarts
)

console = Console()


def analyze_deployment_rca(deployment_name: str, namespace: str):
    try:
        apps = get_apps_v1()
        core = get_core_v1()
        deployment = apps.read_namespaced_deployment(
            deployment_name,
            namespace
        )
        pods = deployment_pods(core, deployment, namespace)
        replicasets = deployment_replicasets(
            apps,
            deployment,
            namespace
        )
        events = list_deployment_events(
            core,
            deployment_name,
            namespace
        )
        log_signals = collect_log_signals(
            core,
            pods,
            namespace
        )
    except Exception as e:
        console.print(
            f"[red]Failed to run RCA:[/red] {e}"
        )
        return

    candidates = build_root_cause_candidates(
        pods,
        replicasets,
        events,
        log_signals
    )

    print_rca_report(
        deployment_name,
        namespace,
        replicasets,
        candidates
    )


def list_deployment_events(core, deployment_name, namespace):
    events = []

    try:
        response = core.list_namespaced_event(namespace=namespace)
    except Exception:
        return events

    for event in response.items:
        involved = event.involved_object
        message = event.message or ""

        if (
            deployment_name in message
            or involved.name == deployment_name
        ):
            events.append(event)

    return events


def collect_log_signals(core, pods, namespace):
    signals = {
        "timeout": 0,
        "connection": 0,
        "exception": 0,
        "permission": 0
    }

    for pod in pods[:3]:
        for container in pod.spec.containers[:2]:
            try:
                logs = core.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=namespace,
                    container=container.name,
                    tail_lines=80
                )
            except Exception:
                continue

            text = logs.lower()
            signals["timeout"] += text.count("timeout")
            signals["connection"] += text.count("connection refused")
            signals["exception"] += text.count("exception")
            signals["permission"] += text.count("permission denied")

    return signals


def build_root_cause_candidates(
    pods,
    replicasets,
    events,
    log_signals
):
    candidates = []
    restarts = sum(total_restarts(pod) for pod in pods)
    ooms = sum(oom_events(pod) for pod in pods)
    crashloops = sum(1 for pod in pods if is_crash_looping(pod))
    event_text = " ".join(
        f"{event.reason} {event.message}"
        for event in events
    ).lower()

    if ooms:
        candidates.append(
            ("Memory exhaustion", min(95, 70 + ooms * 5))
        )

    if crashloops:
        candidates.append(
            ("Application crash loop", min(90, 65 + crashloops * 10))
        )

    if restarts and "back-off" in event_text:
        candidates.append(
            ("Container repeatedly failing after startup", 80)
        )

    if len(replicasets) >= 2:
        current = replicasets[0].spec.template.spec.containers[0]
        previous = replicasets[1].spec.template.spec.containers[0]

        if current.image != previous.image:
            candidates.append(("Image regression", 65))

        if configmap_refs(current) != configmap_refs(previous):
            candidates.append(("ConfigMap change", 60))

        if secret_refs(current) != secret_refs(previous):
            candidates.append(("Secret reference change", 55))

        if (
            resource_limits(current)
            != resource_limits(previous)
        ):
            candidates.append(("Resource limit change", 60))

    if log_signals["timeout"] or log_signals["connection"]:
        candidates.append(("Dependency timeout", 45))

    if log_signals["permission"]:
        candidates.append(("Permission or credentials issue", 50))

    if "failedscheduling" in event_text:
        candidates.append(("Scheduling or capacity constraint", 70))

    if not candidates:
        candidates.append(("No dominant root cause detected", 20))

    deduped = {}
    for name, confidence in candidates:
        deduped[name] = max(confidence, deduped.get(name, 0))

    return sorted(
        deduped.items(),
        key=lambda item: item[1],
        reverse=True
    )


def resource_limits(container):
    return (
        container.resources.limits
        if container.resources and container.resources.limits
        else {}
    )


def print_rca_report(
    deployment_name,
    namespace,
    replicasets,
    candidates
):
    console.print("[bold cyan]Root Cause Candidates[/bold cyan]")
    console.print(f"Deployment: {namespace}/{deployment_name}")

    if replicasets:
        console.print(
            f"Current Revision: {revision_label(replicasets[0])}"
        )

    table = Table(title="RCA")
    table.add_column("Rank")
    table.add_column("Candidate")
    table.add_column("Confidence")

    for index, (candidate, confidence) in enumerate(
        candidates,
        start=1
    ):
        table.add_row(
            str(index),
            candidate,
            f"{confidence}%"
        )

    console.print()
    console.print(table)
