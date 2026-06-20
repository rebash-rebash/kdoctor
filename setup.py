from setuptools import find_packages, setup

setup(
    name="kdoctor",
    version="0.1.0",
    packages=find_packages(exclude=["kdoctor.venv", "kdoctor.venv.*"]),
    install_requires=["typer", "rich", "kubernetes"],
    entry_points={"console_scripts": ["kdoctor=kdoctor.main:app"]},
)
