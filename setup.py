#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="queuectl",
    version="1.0.0",
    description="CLI-based background job queue system",
    author="QueueCTL Team",
    packages=find_packages(),
    install_requires=[
        "click==8.1.7",
        "fastapi==0.115.2",
        "uvicorn==0.30.6",
        "tabulate==0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "queuectl=core.main:cli",
        ],
    },
    python_requires=">=3.7",
)

