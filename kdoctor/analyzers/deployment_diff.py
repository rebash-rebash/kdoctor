from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1
from kdoctor.utils.output import console, render


def compare_revisions(
    deployment_name, namespace, revision1, revision2, output_format: str = None
):

    apps = get_apps_v1()

    deployment = apps.read_namespaced_deployment(deployment_name, namespace)

    deployment_uid = deployment.metadata.uid

    rs1 = None
    rs2 = None

    replicasets = apps.list_namespaced_replica_set(namespace)

    for rs in replicasets.items:

        owners = rs.metadata.owner_references or []

        is_owned = False

        for owner in owners:

            if owner.uid == deployment_uid:
                is_owned = True
                break

        if not is_owned:
            continue

        annotations = rs.metadata.annotations or {}

        revision = annotations.get("deployment.kubernetes.io/revision")

        if revision == revision1:
            rs1 = rs

        if revision == revision2:
            rs2 = rs

    if not rs1:

        console.print(f"[red]Revision {revision1} not found[/red]")
        return

    if not rs2:

        console.print(f"[red]Revision {revision2} not found[/red]")
        return

    compare_replicasets(rs1, rs2, output_format=output_format)


def compare_replicasets(rs1, rs2, output_format: str = None):

    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    differences = []

    if c1.image != c2.image:
        differences.append(
            {
                "field": "image",
                "revision1": c1.image,
                "revision2": c2.image,
                "tag1": extract_tag(c1.image),
                "tag2": extract_tag(c2.image),
            }
        )

    requests1 = c1.resources.requests or {}
    requests2 = c2.resources.requests or {}

    if requests1 != requests2:
        differences.append(
            {
                "field": "resource_requests",
                "revision1": requests1,
                "revision2": requests2,
            }
        )

    limits1 = c1.resources.limits or {}
    limits2 = c2.resources.limits or {}

    if limits1 != limits2:
        differences.append(
            {"field": "resource_limits", "revision1": limits1, "revision2": limits2}
        )

    env1 = {env.name: env.value for env in (c1.env or [])}
    env2 = {env.name: env.value for env in (c2.env or [])}

    env_diffs = []
    all_envs = set(env1.keys()) | set(env2.keys())

    for key in sorted(all_envs):
        if env1.get(key) != env2.get(key):
            env_diffs.append(
                {"name": key, "revision1": env1.get(key), "revision2": env2.get(key)}
            )

    if env_diffs:
        differences.append({"field": "environment_variables", "values": env_diffs})

    cm1 = get_configmaps(c1)
    cm2 = get_configmaps(c2)

    if cm1 != cm2:
        differences.append({"field": "configmaps", "revision1": cm1, "revision2": cm2})

    secret1 = get_secrets(c1)
    secret2 = get_secrets(c2)

    if secret1 != secret2:
        differences.append(
            {"field": "secrets", "revision1": secret1, "revision2": secret2}
        )

    risk, reasons = assess_diff_risk(rs1, rs2)

    if output_format and render(
        {"differences": differences, "risk": risk, "reasons": reasons}, output_format
    ):
        return

    console.print()

    table = Table(title="Deployment Diff")
    table.add_column("Field")
    table.add_column("Revision 1", overflow="fold")
    table.add_column("Revision 2", overflow="fold")

    if c1.image != c2.image:
        table.add_row("Image", c1.image, c2.image)
        table.add_row("Tag", extract_tag(c1.image), extract_tag(c2.image))

    if requests1 != requests2:
        table.add_row(
            "CPU Request", requests1.get("cpu", "-"), requests2.get("cpu", "-")
        )
        table.add_row(
            "Memory Request", requests1.get("memory", "-"), requests2.get("memory", "-")
        )

    if limits1 != limits2:
        table.add_row("CPU Limit", limits1.get("cpu", "-"), limits2.get("cpu", "-"))
        table.add_row(
            "Memory Limit", limits1.get("memory", "-"), limits2.get("memory", "-")
        )

    for env_diff in env_diffs:
        table.add_row(
            f"ENV:{env_diff['name']}",
            str(env_diff["revision1"]),
            str(env_diff["revision2"]),
        )

    if cm1 != cm2:
        table.add_row(
            "ConfigMaps", ",".join(cm1) if cm1 else "-", ",".join(cm2) if cm2 else "-"
        )

    if secret1 != secret2:
        table.add_row(
            "Secrets",
            ",".join(secret1) if secret1 else "-",
            ",".join(secret2) if secret2 else "-",
        )

    console.print(table)

    print_change_summary(rs1, rs2)
    print_risk_assessment(rs1, rs2)


def assess_diff_risk(rs1, rs2):
    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    risk = "LOW"
    reasons = []

    if c1.image != c2.image:
        risk = "MEDIUM"
        reasons.append("Container image changed")

    if (c1.resources.requests or {}) != (c2.resources.requests or {}):
        risk = "MEDIUM"
        reasons.append("Resource requests changed")

    if (c1.resources.limits or {}) != (c2.resources.limits or {}):
        risk = "HIGH"
        reasons.append("Resource limits changed")

    return risk, reasons


def print_risk_assessment(rs1, rs2):

    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    risk = "LOW"

    reasons = []

    if c1.image != c2.image:

        risk = "MEDIUM"

        reasons.append("Container image changed")

    if (c1.resources.requests or {}) != (c2.resources.requests or {}):

        risk = "MEDIUM"

        reasons.append("Resource requests changed")

    if (c1.resources.limits or {}) != (c2.resources.limits or {}):

        risk = "HIGH"

        reasons.append("Resource limits changed")

    console.print()
    console.print("[bold yellow]Risk Assessment[/bold yellow]")

    console.print(f"Risk Level: {risk}")

    for reason in reasons:

        console.print(f"• {reason}")


def extract_tag(image: str):

    if ":" not in image:
        return "latest"

    return image.split(":")[-1]


def get_configmaps(container):

    configmaps = []

    for env in container.env or []:

        value_from = getattr(env, "value_from", None)

        if value_from and value_from.config_map_key_ref:

            configmaps.append(value_from.config_map_key_ref.name)

    return sorted(list(set(configmaps)))


def get_secrets(container):

    secrets = []

    for env in container.env or []:

        value_from = getattr(env, "value_from", None)

        if value_from and value_from.secret_key_ref:

            secrets.append(value_from.secret_key_ref.name)

    return sorted(list(set(secrets)))


def print_change_summary(rs1, rs2):

    c1 = rs1.spec.template.spec.containers[0]
    c2 = rs2.spec.template.spec.containers[0]

    console.print()
    console.print("[bold cyan]Change Summary[/bold cyan]")

    changes = []

    if c1.image != c2.image:
        changes.append("Container image changed")

    if (c1.resources.requests or {}) != (c2.resources.requests or {}):
        changes.append("Resource requests changed")

    if (c1.resources.limits or {}) != (c2.resources.limits or {}):
        changes.append("Resource limits changed")

    if not changes:

        console.print("[green]No significant changes detected[/green]")

        return

    for item in changes:

        console.print(f"• {item}")
