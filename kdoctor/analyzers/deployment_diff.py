from kubernetes import client
from kubernetes import config


from rich.console import Console
from rich.table import Table

console = Console()


def compare_revisions(
    deployment_name,
    namespace,
    revision1,
    revision2
):

    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

    apps = client.AppsV1Api()

    deployment = apps.read_namespaced_deployment(
        deployment_name,
        namespace
    )

    deployment_uid = deployment.metadata.uid

    rs1 = None
    rs2 = None

    replicasets = apps.list_namespaced_replica_set(
        namespace
    )

    for rs in replicasets.items:

        owners = (
            rs.metadata.owner_references
            or []
        )

        is_owned = False

        for owner in owners:

            if owner.uid == deployment_uid:
                is_owned = True
                break

        if not is_owned:
            continue

        annotations = (
            rs.metadata.annotations
            or {}
        )

        revision = annotations.get(
            "deployment.kubernetes.io/revision"
        )

        if revision == revision1:
            rs1 = rs

        if revision == revision2:
            rs2 = rs

    if not rs1:

        console.print(
            f"[red]Revision {revision1} not found[/red]"
        )
        return

    if not rs2:

        console.print(
            f"[red]Revision {revision2} not found[/red]"
        )
        return

    compare_replicasets(
        rs1,
        rs2
    )

def compare_replicasets(
    rs1,
    rs2
):

    console.print()

    table = Table(
        title="Deployment Diff"
    )

    table.add_column("Field")
    table.add_column(
        "Revision 1",
        overflow="fold"
    )

    table.add_column(
        "Revision 2",
        overflow="fold"
    )

    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    # --------------------------------------------------
    # Image
    # --------------------------------------------------

    if c1.image != c2.image:

        table.add_row(
            "Image",
            c1.image,
            c2.image
        )

        table.add_row(
            "Tag",
            extract_tag(c1.image),
            extract_tag(c2.image)
        )

    # --------------------------------------------------
    # Requests
    # --------------------------------------------------

    requests1 = (
        c1.resources.requests or {}
    )

    requests2 = (
        c2.resources.requests or {}
    )

    if requests1 != requests2:

        table.add_row(
            "CPU Request",
            requests1.get("cpu", "-"),
            requests2.get("cpu", "-")
        )

        table.add_row(
            "Memory Request",
            requests1.get("memory", "-"),
            requests2.get("memory", "-")
        )

    # --------------------------------------------------
    # Limits
    # --------------------------------------------------

    limits1 = (
        c1.resources.limits or {}
    )

    limits2 = (
        c2.resources.limits or {}
    )

    if limits1 != limits2:

        table.add_row(
            "CPU Limit",
            limits1.get("cpu", "-"),
            limits2.get("cpu", "-")
        )

        table.add_row(
            "Memory Limit",
            limits1.get("memory", "-"),
            limits2.get("memory", "-")
        )

    # --------------------------------------------------
    # Environment Variables
    # --------------------------------------------------

    env1 = {
        env.name: env.value
        for env in (c1.env or [])
    }

    env2 = {
        env.name: env.value
        for env in (c2.env or [])
    }

    all_envs = (
        set(env1.keys())
        | set(env2.keys())
    )

    for key in sorted(all_envs):

        if env1.get(key) != env2.get(key):

            table.add_row(
                f"ENV:{key}",
                str(env1.get(key)),
                str(env2.get(key))
            )

    # --------------------------------------------------
    # ConfigMaps
    # --------------------------------------------------

    cm1 = get_configmaps(c1)
    cm2 = get_configmaps(c2)

    if cm1 != cm2:

        table.add_row(
            "ConfigMaps",
            ",".join(cm1) if cm1 else "-",
            ",".join(cm2) if cm2 else "-"
        )

    # --------------------------------------------------
    # Secrets
    # --------------------------------------------------

    secret1 = get_secrets(c1)
    secret2 = get_secrets(c2)

    if secret1 != secret2:

        table.add_row(
            "Secrets",
            ",".join(secret1) if secret1 else "-",
            ",".join(secret2) if secret2 else "-"
        )

    console.print(table)

    print_change_summary(
        rs1,
        rs2
    )
    print_risk_assessment(
        rs1,
        rs2
    )

def print_risk_assessment(
    rs1,
    rs2
):

    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    risk = "LOW"

    reasons = []

    if c1.image != c2.image:

        risk = "MEDIUM"

        reasons.append(
            "Container image changed"
        )

    if (
        (c1.resources.requests or {})
        !=
        (c2.resources.requests or {})
    ):

        risk = "MEDIUM"

        reasons.append(
            "Resource requests changed"
        )

    if (
        (c1.resources.limits or {})
        !=
        (c2.resources.limits or {})
    ):

        risk = "HIGH"

        reasons.append(
            "Resource limits changed"
        )

    console.print()
    console.print(
        "[bold yellow]Risk Assessment[/bold yellow]"
    )

    console.print(
        f"Risk Level: {risk}"
    )

    for reason in reasons:

        console.print(
            f"• {reason}"
        )
        
def extract_tag(
    image: str
):

    if ":" not in image:
        return "latest"

    return image.split(":")[-1]

def get_configmaps(
    container
):

    configmaps = []

    for env in (
        container.env or []
    ):

        value_from = getattr(
            env,
            "value_from",
            None
        )

        if (
            value_from
            and value_from.config_map_key_ref
        ):

            configmaps.append(
                value_from.config_map_key_ref.name
            )

    return sorted(
        list(set(configmaps))
    )

def get_secrets(
    container
):

    secrets = []

    for env in (
        container.env or []
    ):

        value_from = getattr(
            env,
            "value_from",
            None
        )

        if (
            value_from
            and value_from.secret_key_ref
        ):

            secrets.append(
                value_from.secret_key_ref.name
            )

    return sorted(
        list(set(secrets))
    )

def print_change_summary(
    rs1,
    rs2
):

    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    console.print()
    console.print(
        "[bold cyan]Change Summary[/bold cyan]"
    )

    changes = []

    if c1.image != c2.image:
        changes.append(
            "Container image changed"
        )

    if (
        (c1.resources.requests or {})
        !=
        (c2.resources.requests or {})
    ):
        changes.append(
            "Resource requests changed"
        )

    if (
        (c1.resources.limits or {})
        !=
        (c2.resources.limits or {})
    ):
        changes.append(
            "Resource limits changed"
        )

    if not changes:

        console.print(
            "[green]No significant changes detected[/green]"
        )

        return

    for item in changes:

        console.print(
            f"• {item}"
        )

