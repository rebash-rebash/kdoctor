from rich.console import Console
from rich.table import Table

from kubernetes import client
from kubernetes import config

console = Console()


def show_rollout_history(
    deployment_name: str,
    namespace: str
):

    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

    apps = client.AppsV1Api()

    deployment = (
        apps.read_namespaced_deployment(
            deployment_name,
            namespace
        )
    )

    replicasets = (
        apps.list_namespaced_replica_set(
            namespace
        )
    )

    deployment_uid = (
        deployment.metadata.uid
    )

    owned_rs = []

    for rs in replicasets.items:

        owners = (
            rs.metadata.owner_references
            or []
        )

        for owner in owners:

            if (
                owner.uid
                == deployment_uid
            ):

                owned_rs.append(
                    rs
                )

    owned_rs.sort(
        key=lambda rs: (
            rs.metadata.creation_timestamp
        ),
        reverse=True
    )

    table = Table(
        title="Deployment Rollout History"
    )

    table.add_column("Revision")
    table.add_column("ReplicaSet")
    table.add_column("Image")
    table.add_column("Created")

    for rs in owned_rs:

        revision = (
            rs.metadata.annotations.get(
                "deployment.kubernetes.io/revision",
                "?"
            )
        )

        image = (
            rs.spec.template
            .spec.containers[0]
            .image
        )

        created = str(
            rs.metadata.creation_timestamp
        )

        table.add_row(
            revision,
            rs.metadata.name,
            image,
            created
        )

    console.print(table)