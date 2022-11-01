"""Setup delta.raster_api."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    "titiler.pgstac==0.1.0.a9",
    "titiler.application>=0.5,<0.6",
    "starlette-cramjam>=0.1.0,<0.2",
    "importlib_resources>=1.1.0;python_version<'3.9'",
    "aws_xray_sdk>=2.6.0,<3",
    "aws-lambda-powertools>=1.18.0",
]

extra_reqs = {
    # https://www.psycopg.org/psycopg3/docs/api/pq.html#pq-module-implementations
    "psycopg": ["psycopg[pool]"],  # pure python implementation
    "psycopg-c": ["psycopg[c,pool]"],  # C implementation of the libpq wrapper
    "psycopg-binary": ["psycopg[binary,pool]"],  # pre-compiled C implementation
    "test": ["pytest", "pytest-cov", "pytest-asyncio", "requests"],
}


setup(
    name="delta.raster_api",
    description="",
    python_requires=">=3.7",
    packages=find_namespace_packages(exclude=["tests*"]),
    package_data={"delta": ["raster/templates/*.html"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
