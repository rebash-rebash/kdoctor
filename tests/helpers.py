from types import SimpleNamespace


def obj(**kwargs):
    return SimpleNamespace(**kwargs)


def metadata(name, namespace="default", labels=None, uid=None, annotations=None):
    return obj(
        name=name,
        namespace=namespace,
        labels=labels or {},
        uid=uid,
        annotations=annotations or {},
    )


def resource_requirements(requests=None, limits=None):
    return obj(requests=requests, limits=limits)


def container(
    name="app",
    image="example/app:1.0.0",
    requests=None,
    limits=None,
    env=None,
    env_from=None,
    liveness_probe=True,
    readiness_probe=True,
    startup_probe=True,
    security_context=None,
):
    return obj(
        name=name,
        image=image,
        resources=resource_requirements(requests, limits),
        env=env or [],
        env_from=env_from or [],
        liveness_probe=liveness_probe,
        readiness_probe=readiness_probe,
        startup_probe=startup_probe,
        security_context=security_context,
    )


def deployment(
    name="api",
    namespace="default",
    uid="deployment-1",
    replicas=2,
    containers=None,
    pod_security_context=None,
    selector=None,
):
    return obj(
        metadata=metadata(name, namespace, uid=uid),
        spec=obj(
            replicas=replicas,
            selector=obj(match_labels=selector or {"app": name}),
            template=obj(
                spec=obj(
                    containers=containers or [container()],
                    security_context=pod_security_context,
                )
            ),
        ),
        status=obj(ready_replicas=replicas),
    )


def replicaset(name="api-abc123", replicas=2, containers=None, revision="1"):
    return obj(
        metadata=metadata(
            name, annotations={"deployment.kubernetes.io/revision": revision}
        ),
        spec=obj(
            replicas=replicas,
            template=obj(spec=obj(containers=containers or [container()])),
        ),
    )


def env(name, value=None, value_from=None):
    return obj(name=name, value=value, value_from=value_from)


def configmap_key_ref(name, key):
    return obj(
        config_map_key_ref=obj(name=name, key=key),
        secret_key_ref=None,
        field_ref=None,
        resource_field_ref=None,
    )


def secret_key_ref(name, key):
    return obj(
        config_map_key_ref=None,
        secret_key_ref=obj(name=name, key=key),
        field_ref=None,
        resource_field_ref=None,
    )
