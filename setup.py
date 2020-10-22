#!/usr/bin/env python3

import glob
import os
from pathlib import Path
from setuptools import setup, find_packages

from bldr.version import get_version


def get_package_data():
    package_data = []
    for path in glob.glob('bldr/data/**/*', recursive=True):
        if os.path.isfile(path):
            package_data.append(path.split('/', 1)[1])
    return package_data


with open("README.md") as readme:
    LONG_DESCRIPTION = readme.read()

setup(
    name='bldr',
    author_email="SD@labs.quest.com",
    author="BLDR Developers",
    url="https://www.github.com/QSFT/bldr",
    description="Build debian packages in a clean docker environment",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    version=get_version(),
    packages=find_packages(include=["bldr*"]),
    install_requires=Path('requirements.txt').read_text(),
    entry_points={
        "console_scripts": [
            "bldr = bldr.cli:main",
        ]
    },
    extras_require={
        'dev': Path('requirements-dev.txt').read_text(),
    },
    python_requires=">=3.6",
    package_data={'bldr': [
        'VERSION',
    ] + get_package_data()},
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)
