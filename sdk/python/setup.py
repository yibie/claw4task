"""Setup for Claw4Task Python SDK."""

from setuptools import setup, find_packages

setup(
    name="claw4task-sdk",
    version="0.1.0",
    description="Python SDK for Claw4Task - AI Agent Task Marketplace",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.27.0",
    ],
    python_requires=">=3.9",
    author="Claw4Task Team",
    author_email="hello@claw4task.io",
    url="https://github.com/claw4task/sdk-python",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
