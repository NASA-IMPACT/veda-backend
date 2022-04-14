"""Setup stac_fastapi
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    # from eoAPI:
    # "stac-fastapi.api~=2.3",
    # "stac-fastapi.types~=2.3",
    # "stac-fastapi.extensions~=2.3",
    # "stac-fastapi.pgstac~=2.3",
    # We use unreleased stac-fastapi which has a better fastapi requirement definition (fix geojson-pydantic and starlette issues)
    "stac-fastapi.api @ git+https://github.com/stac-utils/stac-fastapi/@81015a153c1d9f36d8e12f17a1bf67370396f472#egg=stac-fastapi.api&subdirectory=stac_fastapi/api",
    "stac-fastapi.extensions @ git+https://github.com/stac-utils/stac-fastapi/@81015a153c1d9f36d8e12f17a1bf67370396f472#egg=stac-fastapi.extensions&subdirectory=stac_fastapi/extensions",
    "stac-fastapi.pgstac @ git+https://github.com/stac-utils/stac-fastapi/@81015a153c1d9f36d8e12f17a1bf67370396f472#egg=stac-fastapi.pgstac&subdirectory=stac_fastapi/pgstac",
    "stac-fastapi.types @ git+https://github.com/stac-utils/stac-fastapi/@81015a153c1d9f36d8e12f17a1bf67370396f472#egg=stac-fastapi.types&subdirectory=stac_fastapi/types",
    "jinja2>=2.11.2,<4.0.0",
    "starlette-cramjam>=0.1.0.a0,<0.2",
    "importlib_resources>=1.1.0;python_version<'3.9'",
]

extra_reqs = {
    "test": ["pytest", "pytest-cov", "pytest-asyncio", "requests"],
}


setup(
    name="delta.stac_api",
    description="",
    python_requires=">=3.7",
    packages=find_namespace_packages(exclude=["tests*"]),
    package_data={"delta": ["stac/templates/*.html"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
