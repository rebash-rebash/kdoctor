import unittest

from kdoctor.analyzers import deployment_drift
from tests.helpers import (
    configmap_key_ref,
    container,
    deployment,
    env,
    replicaset,
    secret_key_ref
)


class DeploymentDriftTest(unittest.TestCase):
    def test_compare_live_to_replicaset_detects_core_drift_fields(self):
        expected_container = container(
            name="api",
            image="registry.example.com/api:1.0.0",
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "512Mi"},
            env=[
                env("MODE", "stable"),
                env("CONFIG_VALUE", value_from=configmap_key_ref("api-config", "value")),
                env("TOKEN", value_from=secret_key_ref("api-secret", "token"))
            ]
        )
        live_container = container(
            name="api",
            image="registry.example.com/api:2.0.0",
            requests={"cpu": "200m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "1Gi"},
            env=[
                env("MODE", "canary"),
                env("CONFIG_VALUE", value_from=configmap_key_ref("api-config-v2", "value")),
                env("TOKEN", value_from=secret_key_ref("api-secret-v2", "token"))
            ]
        )

        findings = deployment_drift.compare_live_to_replicaset(
            deployment(replicas=5, containers=[live_container]),
            replicaset(replicas=2, containers=[expected_container])
        )
        fields = {
            finding["field"]
            for finding in findings
        }

        self.assertIn("spec.replicas", fields)
        self.assertIn("containers.api.image", fields)
        self.assertIn("containers.api.env", fields)
        self.assertIn("containers.api.resources.requests", fields)
        self.assertIn("containers.api.resources.limits", fields)
        self.assertIn("containers.api.configmaps", fields)
        self.assertIn("containers.api.secrets", fields)

    def test_compare_live_to_replicaset_returns_no_findings_when_equal(self):
        app = container(
            name="api",
            image="registry.example.com/api:1.0.0",
            requests={"cpu": "100m"},
            limits={"memory": "256Mi"},
            env=[env("MODE", "stable")]
        )

        findings = deployment_drift.compare_live_to_replicaset(
            deployment(replicas=2, containers=[app]),
            replicaset(replicas=2, containers=[app])
        )

        self.assertEqual(findings, [])

    def test_compare_live_to_replicaset_detects_missing_container(self):
        findings = deployment_drift.compare_live_to_replicaset(
            deployment(
                containers=[
                    container(name="api")
                ]
            ),
            replicaset(
                containers=[
                    container(name="api"),
                    container(name="worker")
                ]
            )
        )

        self.assertEqual(
            findings,
            [
                {
                    "field": "containers.worker",
                    "expected": "present",
                    "actual": "missing"
                }
            ]
        )


if __name__ == "__main__":
    unittest.main()
