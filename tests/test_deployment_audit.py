import unittest

from kdoctor.analyzers import deployment_audit
from tests.helpers import container, deployment, obj


class DeploymentAuditTest(unittest.TestCase):
    def test_evaluate_deployment_reports_best_practice_findings(self):
        insecure_container = container(
            name="api",
            image="registry.example.com/payment-api:latest",
            requests=None,
            limits=None,
            liveness_probe=None,
            readiness_probe=None,
            startup_probe=None,
            security_context=obj(
                run_as_non_root=None,
                run_as_user=0,
                privileged=True
            )
        )

        result = deployment_audit.evaluate_deployment(
            deployment(containers=[insecure_container])
        )
        findings = {
            item["finding"]
            for item in result["findings"]
        }

        self.assertIn("Missing requests", findings)
        self.assertIn("Missing limits", findings)
        self.assertIn("Missing liveness probe", findings)
        self.assertIn("Missing readiness probe", findings)
        self.assertIn("Missing startup probe", findings)
        self.assertIn("Running as root", findings)
        self.assertIn("Privileged container", findings)
        self.assertIn("Uses latest image tag", findings)
        self.assertLess(result["score"], 100)
        self.assertEqual(result["risk"], "HIGH")

    def test_evaluate_deployment_skips_system_sidecars(self):
        sidecar = container(
            name="istio-proxy",
            image="proxy:latest",
            requests=None,
            limits=None,
            liveness_probe=None,
            readiness_probe=None,
            security_context=obj(
                run_as_non_root=None,
                run_as_user=0,
                privileged=True
            )
        )
        app = container(
            name="api",
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "512Mi"},
            security_context=obj(
                run_as_non_root=True,
                run_as_user=1000,
                privileged=False
            )
        )

        result = deployment_audit.evaluate_deployment(
            deployment(containers=[sidecar, app])
        )

        self.assertEqual(result["findings"], [])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["risk"], "LOW")

    def test_runs_as_root_honors_non_root_context(self):
        self.assertFalse(
            deployment_audit.runs_as_root(
                obj(run_as_non_root=True, run_as_user=None),
                None
            )
        )
        self.assertFalse(
            deployment_audit.runs_as_root(
                obj(run_as_non_root=None, run_as_user=1000),
                None
            )
        )
        self.assertTrue(
            deployment_audit.runs_as_root(
                obj(run_as_non_root=None, run_as_user=0),
                None
            )
        )


if __name__ == "__main__":
    unittest.main()
