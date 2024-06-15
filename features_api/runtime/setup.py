"""Setup veda.raster_api."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    "boto3",
    "pydantic>=2.4,<3.0",
    "pydantic-settings~=2.0",
    "tipg==0.6.3",
    "aws_xray_sdk>=2.6.0,<3",
    "aws-lambda-powertools>=1.18.0",
]

extra_reqs = {
    # https://www.psycopg.org/psycopg3/docs/api/pq.html#pq-module-implementations
    "psycopg": ["psycopg[pool]"],  # pure python implementation
    "psycopg-c": ["psycopg[c,pool]"],  # C implementation of the libpq wrapper
    "psycopg-binary": ["psycopg[binary,pool]"],  # pre-compiled C implementation
    "test": ["pytest", "pytest-cov", "pytest-asyncio", "requests", "brotlipy"],
}


setup(
    name="veda.features_api",
    description="",
    python_requires=">=3.9",
    packages=find_namespace_packages(exclude=["tests*"]),
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
