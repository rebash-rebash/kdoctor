<!--
KDoctor — Your Kubernetes Troubleshooting Assistant
Production-ready README intended for an open-source CNCF-style project.
Replace OWNER/REPO in badges with your repository values.
-->

# KDoctor
Your Kubernetes Troubleshooting Assistant

[![Build](https://img.shields.io/github/actions/workflow/status/OWNER/REPO/ci.yml?branch=main&label=build&style=flat-square)](https://github.com/OWNER/REPO/actions)
[![PyPI](https://img.shields.io/pypi/v/kdoctor?style=flat-square)](https://pypi.org/project/kdoctor)
[![Python Versions](https://img.shields.io/pypi/pyversions/kdoctor?style=flat-square)](https://pypi.org/project/kdoctor)
[![License](https://img.shields.io/badge/license-SEE_LICENSE_FILE-blue?style=flat-square)](LICENSE)
[![Coverage](https://img.shields.io/codecov/c/gh/OWNER/REPO?style=flat-square)](https://codecov.io/gh/OWNER/REPO)

KDoctor is a Kubernetes diagnostics and troubleshooting CLI for DevOps, Platform, SRE, and Cloud Engineers. It aggregates cluster, pod, and deployment signals into concise health scores, risk assessments, and prioritized recommendations — reducing mean time to resolution (MTTR).

## Table of Contents
- [Why KDoctor?](#why-kdoctor)
- [Highlights](#highlights)
- [Badges](#badges)
- [Features](#features)
- [Feature Matrix](#feature-matrix)
- [Comparison](#comparison)
- [Project Architecture](#project-architecture)
- [Installation](#installation)
- [Local Development](#local-development)
- [Command Reference](#command-reference)
- [Screenshots](#screenshots)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Code of Conduct](#code-of-conduct)
- [License](#license)

## Why KDoctor?
KDoctor helps you quickly identify and diagnose Kubernetes issues without manually running dozens of `kubectl` commands. It provides:

- Actionable outputs: human-friendly health scores and prioritized remediation steps.
- Context-aware analysis: combines events, resource state, and rollout history.
- Extensibility: modular analyzers and a clean client layer for integrations.

## Highlights

- Fast, scriptable CLI built with `typer` and rendered with `rich`.
- Cluster, Pod, and Deployment analysis with risk scoring and recommendations.
- Diff and rollout history tools to accelerate deployment investigations.

## Badges
Replace `OWNER/REPO` with your GitHub repository owner/name in the badge URLs.

## Features

Core commands:

- `kdoctor cluster analyze` — Cluster-level diagnostics and scoring
- `kdoctor cluster analyze --details` — Extended cluster checks
- `kdoctor pod analyze POD_NAME -n NAMESPACE` — Pod-level diagnostics
- `kdoctor deployment investigate DEPLOYMENT_NAME -n NAMESPACE [--deep]` — Deployment investigation
- `kdoctor deployment rollout-history DEPLOYMENT_NAME -n NAMESPACE` — Rollout timeline & revisions
- `kdoctor deployment diff DEPLOYMENT_NAME REV1 REV2 -n NAMESPACE` — Deployment revision diff
- `kdoctor namespace investigate NAMESPACE [--output json|yaml]` — Namespace intelligence, health, risk, and workload hotspots
- `kdoctor deployment rollback-advisor DEPLOYMENT_NAME -n NAMESPACE [--output json|yaml]` — Rollback target and safety assessment
- `kdoctor deployment drift DEPLOYMENT_NAME -n NAMESPACE [--output json|yaml]` — Live deployment drift detection
- `kdoctor deployment audit DEPLOYMENT_NAME -n NAMESPACE [--output json|yaml]` — Kubernetes best practices audit
- `kdoctor incident investigate` — Cluster-wide incident summary and likely cause
- `kdoctor deployment rca DEPLOYMENT_NAME -n NAMESPACE` — Root-cause candidate analysis

Capabilities (high level): node health, pod health scoring, namespace health and risk scoring, probe validation, restart analysis, OOM and CrashLoopBackOff detection, replica and rollout analysis, rollback advice, image/env/resource/secret/ConfigMap drift detection, best-practices audits, incident summaries, root-cause candidates, risk assessment, and recommendations.

## Feature Matrix

| Feature / Command | Cluster Analyze | Namespace Investigate | Pod Analyze | Deployment Investigate | Rollout/Diff | Audit/Drift/RCA | Incident |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Health scoring | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Risk assessment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Node health | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Pod summary | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Restart analysis | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OOM / CrashLoopBackOff detection | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Replica analysis | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Image comparison | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Env / Config diff | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Secret comparison | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Best-practices audit | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Recommendations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Comparison: KDoctor vs kubectl vs Lens vs K9s

| Capability | KDoctor | kubectl | Lens | K9s |
|---|---:|:---:|:---:|:---:|
| Interactive UI | ❌ | ❌ | ✅ | ✅ |
| One-command diagnostics | ✅ | ❌ | ❌ | ❌ |
| Health scoring & risk assessment | ✅ | ❌ | ❌ | ❌ |
| Pod/Container deep analysis | ✅ | ❌ | ✅ | ✅ |
| Deployment diffs & risk summary | ✅ | ❌ | ✅ (partial) | ❌ |
| Automatable CLI output | ✅ | ✅ | ❌ | ❌ |
| Integrations (monitoring, AI) | Planned | Manual | Plugins | Plugins |
| Best for quick triage | ✅ | ✅ | ✅ | ✅ |

Notes: `kubectl` is the canonical control-plane tool; Lens and K9s are interactive UIs. KDoctor focuses on curated, repeatable diagnostics and recommendations useful for automation and on-call triage.

## Project Architecture

KDoctor is a modular Python CLI. Important packages:

- `kdoctor.main` — CLI entrypoint (Typer)
- `kdoctor.analyzers` — cluster, pod, and deployment analyzers (domain checks and scoring)
- `kdoctor.clients.kube_client` — Kubernetes API wrapper
- `kdoctor.commands` — Typer command groups
- `kdoctor.utils.output` — Rich rendering helpers

Mermaid flow:

```mermaid
graph LR
	CLI[`kdoctor CLI`] --> Commands
	Commands --> Analyzers
	Analyzers --> KubeClient
	KubeClient --> Kubernetes
	Analyzers --> Output[Rich Renderer]
	Output --> User
```

Design principles: keep analyzers small and testable, separate I/O/client code, and produce both human-friendly and machine-readable outputs.

## Installation

Install from PyPI:

```bash
pip install kdoctor
```

From source:

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Prerequisites: Python 3.9+, kubeconfig or in-cluster credentials with sufficient RBAC for the checks you intend to run.

## Local Development

```bash
# clone and set up
git clone https://github.com/OWNER/REPO.git
cd REPO
python -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install -e .

# lint, format, and tests
pre-commit install
pre-commit run --all-files
pytest tests
```

Tips: run CLI commands against a test cluster and mock the `kube_client` in unit tests.

## Command Reference

Cluster analysis:

```bash
kdoctor cluster analyze
kdoctor cluster analyze --details
```

Pod analysis:

```bash
kdoctor pod analyze POD_NAME -n NAMESPACE
kdoctor pod analyze-all -n NAMESPACE --critical-only --top 10
```

Namespace intelligence:

```bash
kdoctor namespace investigate NAMESPACE
```

Deployment investigation:

```bash
kdoctor deployment investigate DEPLOYMENT_NAME -n NAMESPACE
kdoctor deployment investigate DEPLOYMENT_NAME -n NAMESPACE --deep
```

Rollout history:

```bash
kdoctor deployment rollout-history DEPLOYMENT_NAME -n NAMESPACE
```

Deployment diff:

```bash
kdoctor deployment diff DEPLOYMENT_NAME REVISION1 REVISION2 -n NAMESPACE
```

Deployment intelligence:

```bash
kdoctor deployment rollback-advisor DEPLOYMENT_NAME -n NAMESPACE [--output json|yaml]
kdoctor deployment drift DEPLOYMENT_NAME -n NAMESPACE [--output json|yaml]
kdoctor deployment audit DEPLOYMENT_NAME -n NAMESPACE [--output json|yaml]
kdoctor deployment rca DEPLOYMENT_NAME -n NAMESPACE
```

Incident investigation:

```bash
kdoctor incident investigate
```

Example outputs:

```text
Health Score: 72/100
Risk: MEDIUM
Top Restarting Deployments: payment-api, worker
OOM Events: payment-api: 2
Missing Limits: 6
Recommendations: Review memory limits and recent rollouts.
```

```text
SAFE TO ROLLBACK
Current Revision: 38
Recommended Revision: 37
Reasons:
- Restart count increased
- OOM events increased
- Resource limits changed
```

```text
Drift Detected
Field: spec.replicas
Expected: 2
Actual: 5
```

Options: `--details` for extended cluster checks and `-n, --namespace` for namespace-scoped pod and deployment commands.

## Screenshots

Add real screenshots to `docs/images/` to illustrate outputs. Current placeholders:

- Cluster Analysis: [docs/images/cluster-analysis.svg](docs/images/cluster-analysis.svg)
- Pod Analysis: [docs/images/pod-analysis.svg](docs/images/pod-analysis.svg)
- Deployment Investigation: [docs/images/deployment-investigation.svg](docs/images/deployment-investigation.svg)

## Roadmap

Planned items:

- Prometheus Integration
- Grafana Integration
- Cost Optimization Recommendations

## Contributing

We welcome contributors. See `CONTRIBUTING.md` for the full workflow, testing guidance, and PR checklist.

High level:

- Open issues for feature proposals or bugs.
- Fork and branch: `git checkout -b feat/my-feature`.
- Add tests and documentation for new behavior.
- Keep PRs focused and include screenshots or sample outputs when relevant.

## Code of Conduct

This project follows the Contributor Covenant. See `CODE_OF_CONDUCT.md` for details.

## Security

Report security issues privately (see `MAINTAINERS.md`), do not publish vulnerabilities publicly until fixed.

## License

See the `LICENSE` file in the repository for full license terms.

## Maintainers

Primary maintainers: replace with actual maintainers in `MAINTAINERS.md`.

---

If you want, I can open a PR with these files or add more docs and CI integrations.
