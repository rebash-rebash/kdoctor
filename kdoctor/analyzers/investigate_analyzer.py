from rich.table import Table

from kdoctor.clients.kube_client import get_core_v1
from kdoctor.utils.output import console

SYSTEM_CONTAINERS = {"istio-proxy", "linkerd-proxy"}


def investigate_pod(pod_name: str, namespace: str):

    v1 = get_core_v1()

    try:
        pod = v1.read_namespaced_pod(pod_name, namespace)

    except Exception as e:

        console.print(f"[red]Failed to fetch pod:[/red] {e}")

        return

    print_header(pod_name, namespace, pod.status.phase)

    analyze_container_status(pod)
    analyze_resources(pod)
    analyze_events(v1, pod_name, namespace)

    analyze_logs(v1, pod)


def print_header(pod_name, namespace, phase):

    table = Table(title="Investigation Report")

    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Pod", pod_name)

    table.add_row("Namespace", namespace)

    table.add_row("Status", phase)

    console.print(table)


def analyze_container_status(pod):

    statuses = pod.status.container_statuses or []

    if not statuses:
        return

    console.print()

    console.print("[bold cyan]Container Analysis[/bold cyan]")

    for status in statuses:

        console.print()

        console.print(f"[bold]{status.name}[/bold]")

        console.print(f"Ready: {status.ready}")

        console.print(f"Restarts: {status.restart_count}")

        if status.restart_count > 0:
            console.print(
                f"[yellow]Warning:[/yellow] Restarted {status.restart_count} times"
            )
            last_terminated = getattr(status.last_state, "terminated", None)
            if last_terminated:
                console.print(f"Previous Exit Code: {last_terminated.exit_code}")
                if last_terminated.exit_code == 137:
                    console.print("[red]OOMKilled detected[/red]")

                    console.print("Likely Cause: Container exceeded memory limit")

                    console.print(
                        "Recommendation: Increase memory limit or optimize memory usage"
                    )

                console.print(f"Previous Exit Code: {last_terminated.exit_code}")

        waiting = getattr(status.state, "waiting", None)

        terminated = getattr(status.state, "terminated", None)

        if waiting:

            reason = waiting.reason

            console.print(f"State: {reason}")

            if reason == "CrashLoopBackOff":

                console.print("[red]CrashLoopBackOff detected[/red]")

                console.print("Likely Cause: Application startup failure")

                console.print("Recommendation: Check application logs")

            elif reason in ["ImagePullBackOff", "ErrImagePull"]:

                console.print("[red]Image Pull Failure[/red]")

                console.print("Likely Cause: Invalid image or registry access issue")

                console.print(
                    "Recommendation: Verify image tag and registry credentials"
                )

            elif reason == "CreateContainerConfigError":

                console.print("[red]Container Configuration Error[/red]")

                console.print("Likely Cause: Missing Secret or ConfigMap")

        if terminated:

            console.print(f"Last Exit Code: {terminated.exit_code}")

            console.print(f"Termination Reason: {terminated.reason}")

            if terminated.reason == "OOMKilled":

                console.print("[red]OOMKilled detected[/red]")

                console.print("Likely Cause: Container exceeded memory limit")

                console.print(
                    "Recommendation: Increase memory limit or optimize memory usage"
                )


def analyze_events(v1, pod_name, namespace):

    try:

        events = v1.list_namespaced_event(
            namespace=namespace, field_selector=f"involvedObject.name={pod_name}"
        )

    except Exception as e:

        console.print(f"[red]Failed to fetch events:[/red] {e}")

        return

    console.print()
    console.print(f"[bold cyan]Events ({len(events.items)})[/bold cyan]")

    if not events.items:
        return

    console.print()
    console.print("[bold cyan]Events[/bold cyan]")

    sorted_events = sorted(
        events.items,
        key=lambda e: (
            e.last_timestamp or e.event_time or e.metadata.creation_timestamp
        ),
        reverse=True,
    )

    for event in sorted_events[:15]:

        console.print(f"[yellow]{event.reason}[/yellow]")

        console.print(f"  {event.message}")


def analyze_resources(pod):

    console.print()
    console.print("[bold cyan]Resource Analysis[/bold cyan]")

    table = Table()

    table.add_column("Container")
    table.add_column("CPU Request")
    table.add_column("Memory Request")
    table.add_column("CPU Limit")
    table.add_column("Memory Limit")

    for container in pod.spec.containers:

        requests = container.resources.requests or {}

        limits = container.resources.limits or {}
        if not requests:
            console.print(
                f"[yellow]{container.name} missing resource requests[/yellow]"
            )

        if not limits:
            console.print(f"[yellow]{container.name} missing resource limits[/yellow]")
        table.add_row(
            container.name,
            requests.get("cpu", "-"),
            requests.get("memory", "-"),
            limits.get("cpu", "-"),
            limits.get("memory", "-"),
        )

    console.print(table)


def analyze_logs(v1, pod):

    console.print()
    console.print("[bold cyan]Log Analysis[/bold cyan]")

    found_anything = False

    for container in pod.spec.containers:
        if container.name in SYSTEM_CONTAINERS:
            continue
        try:

            logs = v1.read_namespaced_pod_log(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                container=container.name,
                tail_lines=100,
            )

        except Exception:
            continue

        findings = detect_log_patterns(logs)

        if not findings:
            continue

        found_anything = True

        console.print()

        console.print(f"[bold]{container.name}[/bold]")

        for finding in findings:

            console.print(f"[yellow]Root Cause Candidate[/yellow]")

            console.print(finding["cause"])

            console.print(f"Evidence: {finding['evidence']}")

            console.print(f"Recommendation: {finding['recommendation']}")

            console.print()

    if not found_anything:

        console.print("No obvious failure patterns detected")


def detect_log_patterns(logs):

    findings = []

    lower_logs = logs.lower()

    if "connection refused" in lower_logs:

        findings.append(
            {
                "cause": "Database or backend service unavailable",
                "evidence": "connection refused",
                "recommendation": "Verify service availability and endpoints",
            }
        )

    if "authentication failed" in lower_logs:

        findings.append(
            {
                "cause": "Invalid credentials",
                "evidence": "authentication failed",
                "recommendation": "Verify username, password, or token",
            }
        )

    if "access denied" in lower_logs:

        findings.append(
            {
                "cause": "Permission issue",
                "evidence": "access denied",
                "recommendation": "Verify RBAC, IAM, or filesystem permissions",
            }
        )

    if "timeout" in lower_logs:

        findings.append(
            {
                "cause": "Network timeout or backend latency",
                "evidence": "timeout",
                "recommendation": "Check network connectivity and backend health",
            }
        )

    if "no such host" in lower_logs:

        findings.append(
            {
                "cause": "DNS resolution failure",
                "evidence": "no such host",
                "recommendation": "Verify DNS and service discovery configuration",
            }
        )

    if "out of memory" in lower_logs:

        findings.append(
            {
                "cause": "Memory exhaustion",
                "evidence": "out of memory",
                "recommendation": "Increase memory limits",
            }
        )
    if "oomkilled" in lower_logs:

        findings.append(
            {
                "cause": "Container memory exhaustion",
                "evidence": "oomkilled",
                "recommendation": "Increase memory limits",
            }
        )
    if "crashloopbackoff" in lower_logs:

        findings.append(
            {
                "cause": "Application startup failure",
                "evidence": "crashloopbackoff",
                "recommendation": "Review startup logs",
            }
        )
    if "certificate" in lower_logs and "expired" in lower_logs:

        findings.append(
            {
                "cause": "Expired certificate",
                "evidence": "certificate expired",
                "recommendation": "Renew certificate",
            }
        )

    return findings
