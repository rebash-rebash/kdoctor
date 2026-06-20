import unittest

from typer.testing import CliRunner

from kdoctor.main import app


runner = CliRunner()


class CliRegistrationTest(unittest.TestCase):
    def assert_help_contains(self, args, expected_commands):
        result = runner.invoke(app, [*args, "--help"])

        self.assertEqual(result.exit_code, 0, result.output)

        for command in expected_commands:
            self.assertIn(command, result.output)

    def test_top_level_commands_are_registered(self):
        self.assert_help_contains(
            [],
            [
                "pod",
                "namespace",
                "deployment",
                "cluster",
                "investigate",
                "incident"
            ]
        )

    def test_deployment_commands_are_registered(self):
        self.assert_help_contains(
            ["deployment"],
            [
                "analyze",
                "analyze-all",
                "investigate",
                "rollout-history",
                "diff",
                "rollback-advisor",
                "drift",
                "audit",
                "rca"
            ]
        )

    def test_namespace_commands_are_registered(self):
        self.assert_help_contains(
            ["namespace"],
            [
                "analyze",
                "investigate"
            ]
        )

    def test_incident_commands_are_registered(self):
        self.assert_help_contains(
            ["incident"],
            [
                "investigate"
            ]
        )

    def test_namespace_option_alias_is_available_on_deployment_commands(self):
        result = runner.invoke(
            app,
            ["deployment", "audit", "--help"]
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--namespace", result.output)
        self.assertIn("-n", result.output)

    def test_output_option_is_available_on_namespace_and_deployment_commands(self):
        result = runner.invoke(
            app,
            ["namespace", "investigate", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

        result = runner.invoke(
            app,
            ["deployment", "rollback-advisor", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

        result = runner.invoke(
            app,
            ["deployment", "drift", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

        result = runner.invoke(
            app,
            ["deployment", "audit", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

    def test_cluster_and_pod_output_options_are_available(self):
        result = runner.invoke(
            app,
            ["cluster", "analyze", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

        result = runner.invoke(
            app,
            ["pod", "analyze", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

    def test_deployment_diff_output_option_is_available(self):
        result = runner.invoke(
            app,
            ["deployment", "diff", "--help"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

    def test_incident_timeout_option_is_registered(self):
        result = runner.invoke(
            app,
            ["incident", "investigate", "--help"]
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--timeout", result.output)


if __name__ == "__main__":
    unittest.main()
