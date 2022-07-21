#! /usr/bin/python
from setuptools import find_packages, setup


setup(
    name="managed-services-integration-tests",
    version="1.0",
    packages=find_packages(include=["utilities"]),
    include_package_data=True,
    install_requires=["openshift", "xmltodict", "urllib3"],
    python_requires=">=3.6",
)
