from setuptools import setup

setup(
    name="kdoctor",
    version="0.1.0",
    packages=["kdoctor"],
    install_requires=[
        "typer",
        "rich",
        "kubernetes"
    ],
    entry_points={
        "console_scripts": [
            "kdoctor=kdoctor.main:app"
        ]
    }
)