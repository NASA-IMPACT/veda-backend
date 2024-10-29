"""Setup stac_fastapi
Based on https://github.com/developmentseed/eoAPI/tree/master/src/eoapi/stac
"""

from setuptools import find_namespace_packages, setup

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    "stac-fastapi-pgstac==2.5.0",
    "jinja2>=2.11.2,<4.0.0",
    "starlette-cramjam>=0.1.0.a0,<0.2",
    "importlib_resources>=1.1.0;python_version<='3.9'",  # https://github.com/cogeotiff/rio-tiler/pull/379
    "pygeoif<=0.8",  # newest release (1.0+ / 09-22-2022) breaks a number of other geo libs
    "aws-lambda-powertools>=1.18.0",
    "aws_xray_sdk>=2.6.0,<3",
    "pystac[validation]==1.10.1",
    "pydantic[dotenv]>1.10.8,<2"
]

extra_reqs = {
    "test": ["pytest", "pytest-cov", "pytest-asyncio", "requests"],
}


setup(
    name="veda.stac_api",
    description="",
    python_requires=">=3.7",
    packages=find_namespace_packages(exclude=["tests*"]),
    package_data={"veda": ["stac/templates/*.html"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
