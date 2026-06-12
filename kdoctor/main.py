import typer

from kdoctor.commands.pod import pod
from kdoctor.commands.namespace import namespace
from kdoctor.commands.deployment import deployment
from kdoctor.commands.cluster import cluster
from kdoctor.commands.investigate import investigate

app = typer.Typer()

app.add_typer(
    pod,
    name="pod"
)

app.add_typer(
    namespace,
    name="namespace"
)

app.add_typer(
    deployment,
    name="deployment"
)

app.add_typer(
    cluster,
    name="cluster"
)

app.add_typer(
    investigate,
    name="investigate"
)

if __name__ == "__main__":
    app()