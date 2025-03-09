# setup.py
from setuptools import setup, find_packages

setup(
    name="ai_eval_server",
    version="0.1",
    packages=find_packages(where="apps/server/src"),
    package_dir={"": "apps/server/src"},
)
