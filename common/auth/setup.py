"""Setup veda_auth
"""

from setuptools import find_packages, setup

inst_reqs = ["cryptography>=42.0.5", "pyjwt>=2.8.0", "fastapi<=0.108.0", "pydantic<2"]

setup(
    name="veda_auth",
    version="0.0.1",
    description="",
    python_requires=">=3.7",
    packages=find_packages(),
    zip_safe=False,
    install_requires=inst_reqs,
    include_package_data=True,
)
