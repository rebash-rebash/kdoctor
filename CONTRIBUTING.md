# Contributing to KDoctor

Thanks for your interest in contributing to KDoctor! We welcome improvements, bug fixes, tests, and documentation contributions.

How to contribute

1. Fork the repository and create a feature branch:

```bash
git clone https://github.com/OWNER/REPO.git
git checkout -b feat/my-feature
```

2. Run tests and linters locally before opening a PR:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pre-commit install
pre-commit run --all-files
pytest
```

3. Write tests for new functionality and keep changes focused.
4. Update the `README.md` and docs where appropriate (examples, flags, outputs).
5. Open a pull request against `main` with a clear description and linking any relevant issues.

PR checklist

- [ ] Tests added/updated and passing
- [ ] Linting/formatting applied
- [ ] Documentation updated
- [ ] Commit messages are clear and atomic

Coding conventions

- Follow Black formatting and Flake8 linting rules where applicable.
- Keep analyzer logic small and testable; mock `kube_client` in unit tests.

Need help?

Open an issue describing the problem or proposal and tag it `help wanted` if you want collaborators to pick it up.
