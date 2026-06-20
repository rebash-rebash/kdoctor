from types import SimpleNamespace
import unittest

from kdoctor.analyzers import incident_analyzer


def obj(**kwargs):
    return SimpleNamespace(**kwargs)


def metadata(name, namespace="default", labels=None, uid=None, annotations=None):
    return obj(
        name=name,
        namespace=namespace,
        labels=labels or {},
        uid=uid,
        annotations=annotations or {}
    )


def pod(name, namespace, labels, restarts=0, oom=False, phase="Running"):
    terminated = (
        obj(reason="OOMKilled", exit_code=137)
        if oom else None
    )
    status = obj(
        restart_count=restarts,
        last_state=obj(terminated=terminated)
    )

    return obj(
        metadata=metadata(name, namespace, labels),
        status=obj(
            phase=phase,
            container_statuses=[status]
        )
    )


def deployment(name, namespace, uid, selector, replicas=2, ready=2):
    return obj(
        metadata=metadata(name, namespace, uid=uid),
        spec=obj(
            replicas=replicas,
            selector=obj(match_labels=selector)
        ),
        status=obj(ready_replicas=ready)
    )


def replicaset(name, owner_uid, revision):
    return obj(
        metadata=obj(
            name=name,
            owner_references=[obj(uid=owner_uid)],
            annotations={
                "deployment.kubernetes.io/revision": str(revision)
            }
        )
    )


class IncidentAnalyzerTest(unittest.TestCase):
    def test_labels_match_requires_all_selector_labels(self):
        self.assertTrue(
            incident_analyzer.labels_match(
                {"app": "api", "tier": "backend"},
                {"app": "api", "tier": "backend", "env": "prod"}
            )
        )
        self.assertFalse(
            incident_analyzer.labels_match(
                {"app": "api", "tier": "backend"},
                {"app": "api"}
            )
        )

    def test_analyze_deployments_uses_in_memory_pod_and_replicaset_indexes(self):
        api = deployment(
            "payment-api",
            "services",
            "deploy-1",
            {"app": "payment-api"},
            replicas=3,
            ready=2
        )
        worker = deployment(
            "worker",
            "services",
            "deploy-2",
            {"app": "worker"},
            replicas=1,
            ready=1
        )
        unrelated = deployment(
            "web",
            "default",
            "deploy-3",
            {"app": "web"},
            replicas=1,
            ready=1
        )

        pods = [
            pod(
                "payment-api-1",
                "services",
                {"app": "payment-api"},
                restarts=4,
                oom=True
            ),
            pod(
                "worker-1",
                "services",
                {"app": "worker"},
                restarts=0
            ),
            pod(
                "payment-api-default",
                "default",
                {"app": "payment-api"},
                restarts=9
            )
        ]
        replicasets = [
            replicaset("payment-api-36", "deploy-1", 36),
            replicaset("payment-api-38", "deploy-1", 38),
            replicaset("worker-7", "deploy-2", 7)
        ]

        reports = incident_analyzer.analyze_deployments(
            [api, worker, unrelated],
            pods,
            replicasets
        )

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["name"], "services/payment-api")
        self.assertEqual(reports[0]["ready"], 2)
        self.assertEqual(reports[0]["desired"], 3)
        self.assertEqual(reports[0]["restarts"], 4)
        self.assertEqual(reports[0]["oom"], 1)
        self.assertEqual(reports[0]["revision"], "38")

    def test_choose_likely_cause_prefers_deployment_regression(self):
        cause = incident_analyzer.choose_likely_cause(
            pod_summary={"pending": ["default/pending"]},
            node_issues=[("node-1", "NotReady")],
            deployment_summary=[
                {
                    "name": "services/payment-api",
                    "revision": "42",
                    "restarts": 3,
                    "oom": 1
                }
            ]
        )

        self.assertEqual(
            cause,
            "Recent rollout or regression in services/payment-api revision 42"
        )


if __name__ == "__main__":
    unittest.main()
