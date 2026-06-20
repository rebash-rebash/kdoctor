SYSTEM_CONTAINERS = {
    "istio-proxy",
    "linkerd-proxy"
}


def label_selector(match_labels):
    if not match_labels:
        return ""

    return ",".join(
        f"{key}={value}"
        for key, value in match_labels.items()
    )


def revision_number(resource):
    annotations = resource.metadata.annotations or {}
    revision = annotations.get(
        "deployment.kubernetes.io/revision",
        "0"
    )

    try:
        return int(revision)
    except ValueError:
        return 0


def revision_label(resource):
    number = revision_number(resource)
    return str(number) if number else "?"


def owned_by(resource, owner_uid):
    for owner in resource.metadata.owner_references or []:
        if owner.uid == owner_uid:
            return True

    return False


def deployment_replicasets(apps, deployment, namespace):
    replicasets = apps.list_namespaced_replica_set(namespace).items
    owned = [
        rs for rs in replicasets
        if owned_by(rs, deployment.metadata.uid)
    ]

    owned.sort(
        key=lambda rs: revision_number(rs),
        reverse=True
    )

    return owned


def deployment_pods(core, deployment, namespace):
    selector = label_selector(
        deployment.spec.selector.match_labels
    )

    return core.list_namespaced_pod(
        namespace=namespace,
        label_selector=selector
    ).items


def total_restarts(pod):
    return sum(
        status.restart_count
        for status in pod.status.container_statuses or []
    )


def ready_containers(pod):
    statuses = pod.status.container_statuses or []

    return sum(1 for status in statuses if status.ready), len(statuses)


def is_crash_looping(pod):
    for status in pod.status.container_statuses or []:
        waiting = getattr(status.state, "waiting", None)

        if waiting and waiting.reason == "CrashLoopBackOff":
            return True

    return False


def oom_events(pod):
    count = 0

    for status in pod.status.container_statuses or []:
        terminated = getattr(status.last_state, "terminated", None)

        if not terminated:
            continue

        if (
            terminated.reason == "OOMKilled"
            or terminated.exit_code == 137
        ):
            count += 1

    return count


def missing_resource_counts(pod):
    missing_requests = 0
    missing_limits = 0

    for container in pod.spec.containers:
        if container.name in SYSTEM_CONTAINERS:
            continue

        resources = container.resources
        requests = resources.requests if resources else None
        limits = resources.limits if resources else None

        if not requests:
            missing_requests += 1

        if not limits:
            missing_limits += 1

    return missing_requests, missing_limits


def container_env(container):
    values = {}

    for env in container.env or []:
        if env.value_from:
            values[env.name] = value_from_ref(env.value_from)
        else:
            values[env.name] = env.value

    return values


def value_from_ref(value_from):
    if value_from.config_map_key_ref:
        ref = value_from.config_map_key_ref
        return f"configmap:{ref.name}/{ref.key}"

    if value_from.secret_key_ref:
        ref = value_from.secret_key_ref
        return f"secret:{ref.name}/{ref.key}"

    if value_from.field_ref:
        return f"field:{value_from.field_ref.field_path}"

    if value_from.resource_field_ref:
        return f"resource:{value_from.resource_field_ref.resource}"

    return "valueFrom"


def configmap_refs(container):
    refs = set()

    for env in container.env or []:
        value_from = env.value_from
        if value_from and value_from.config_map_key_ref:
            refs.add(value_from.config_map_key_ref.name)

    for env_from in container.env_from or []:
        if env_from.config_map_ref:
            refs.add(env_from.config_map_ref.name)

    return sorted(refs)


def secret_refs(container):
    refs = set()

    for env in container.env or []:
        value_from = env.value_from
        if value_from and value_from.secret_key_ref:
            refs.add(value_from.secret_key_ref.name)

    for env_from in container.env_from or []:
        if env_from.secret_ref:
            refs.add(env_from.secret_ref.name)

    return sorted(refs)


def primary_container(template_or_pod_spec):
    containers = template_or_pod_spec.spec.containers
    return containers[0] if containers else None


def image_tag(image):
    tail = image.rsplit("/", 1)[-1]

    if ":" not in tail:
        return "latest"

    return tail.rsplit(":", 1)[-1]
