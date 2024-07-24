"""Setup veda_auth
"""

from setuptools import find_packages, setup


inst_reqs = [
    "cryptography>=42.0.5",
    "pyjwt>=2.8.0",
    "fastapi",
]

print(find_packages())
setup(
    name="vedaAuth",
    version="0.0.1",
    description="",
    python_requires=">=3.7",
    packages=['src'],
    zip_safe=False,
    install_requires=inst_reqs,
    include_package_data=True,
)
