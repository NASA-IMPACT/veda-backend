"""Setup veda-backend."""

from setuptools import find_packages, setup

with open("README.md") as f:
    long_description = f.read()


extra_reqs = {
    "dev": ["pre-commit", "python-dotenv"],
    "deploy": [
        "aws-cdk-lib<3.0.0,>=2.15.0",
        "constructs>=10.0.0,<11.0.0",
        "aws-cdk.aws_apigatewayv2_alpha~=2.15.0a0",
        "aws_cdk.aws_apigatewayv2_integrations_alpha~=2.15.0a0",
        "pydantic",
    ],
    "test": [
        "pytest",
        "pytest-asyncio",
        "httpx==0.23.3",
        "pypgstac==0.7.4",
        "psycopg[binary, pool]",
        "boto3",
        "fastapi",
        "moto",
    ],
}


setup(
    name="veda-backend",
    version="0.6.2",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="",
    author="Development Seed",
    author_email="info@developmentseed.org",
    url="https://github.com/NASA-IMPACT/veda-backend",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    package_data={"veda-backend": ["templates/*.html", "templates/*.xml"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    extras_require=extra_reqs,
)
