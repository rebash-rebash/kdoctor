from typing import Optional

from rich.table import Table

from kdoctor.clients.kube_client import get_apps_v1
from kdoctor.utils.output import console, render


def show_rollout_history(
    deployment_name: str, namespace: str, output_format: Optional[str] = None
):

    apps = get_apps_v1()

    deployment = apps.read_namespaced_deployment(deployment_name, namespace)

    replicasets = apps.list_namespaced_replica_set(namespace)

    deployment_uid = deployment.metadata.uid

    owned_rs = []

    for rs in replicasets.items:

        owners = rs.metadata.owner_references or []

        for owner in owners:

            if owner.uid == deployment_uid:

                owned_rs.append(rs)

    owned_rs.sort(key=lambda rs: (rs.metadata.creation_timestamp), reverse=True)

    revisions = []

    for rs in owned_rs:

        revision = rs.metadata.annotations.get("deployment.kubernetes.io/revision", "?")

        image = rs.spec.template.spec.containers[0].image

        created = str(rs.metadata.creation_timestamp)

        revisions.append(
            {
                "revision": revision,
                "replica_set": rs.metadata.name,
                "image": image,
                "created": created,
            }
        )

    if output_format and render(
        {"deployment": deployment_name, "namespace": namespace, "revisions": revisions},
        output_format,
    ):
        return

    table = Table(title="Deployment Rollout History")

    table.add_column("Revision")
    table.add_column("ReplicaSet")
    table.add_column("Image")
    table.add_column("Created")

    for rev in revisions:

        table.add_row(rev["revision"], rev["replica_set"], rev["image"], rev["created"])

    console.print(table)
