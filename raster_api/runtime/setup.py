"""Setup veda.raster_api."""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    "boto3",
    "rio-tiler==6.5.0",
    "titiler.pgstac==1.3.0",
    "titiler.core>=0.15.5,<0.16",
    "titiler.mosaic>=0.15.5,<0.16",
    "titiler.extensions[cogeo]>=0.15.5,<0.16",
    "starlette-cramjam>=0.3,<0.4",
    "aws_xray_sdk>=2.6.0,<3",
    "aws-lambda-powertools>=1.18.0",
    "python-multipart==0.0.7",
]

extra_reqs = {
    # https://www.psycopg.org/psycopg3/docs/api/pq.html#pq-module-implementations
    "psycopg": ["psycopg[pool]"],  # pure python implementation
    "psycopg-c": ["psycopg[c,pool]"],  # C implementation of the libpq wrapper
    "psycopg-binary": ["psycopg[binary,pool]"],  # pre-compiled C implementation
    "test": ["pytest", "pytest-cov", "pytest-asyncio", "requests", "brotlipy"],
}


setup(
    name="veda.raster_api",
    description="",
    python_requires=">=3.8",
    packages=find_namespace_packages(exclude=["tests*"]),
    package_data={"src": ["templates/*.html", "cmap_data/*.npy"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
