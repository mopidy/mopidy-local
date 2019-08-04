from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall('__([a-z]+)__ = "([^"]+)"', fh.read()))
        return metadata["version"]


setup(
    name="Mopidy-Local",
    version=get_version("mopidy_local/__init__.py"),
    url="https://github.com/mopidy/mopidy-local",
    license="Apache License, Version 2.0",
    author="Stein Magnus Jodal",
    author_email="stein.magnus@jodal.no",
    description=(
        "Mopidy extension for playing music from your local music archive"),
    long_description=open("README.rst").read(),
    packages=find_packages(exclude=["tests", "tests.*"]),
    zip_safe=False,
    include_package_data=True,
    python_requires="> 2.7, < 3",
    install_requires=[
        "setuptools",
        "Mopidy >= 3.0.0a1",
        "Pykka >= 2.0",
    ],
    entry_points={
        "mopidy.ext": [
            "local = mopidy_local:Extension",
        ]
    },
    classifiers=[
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Multimedia :: Sound/Audio :: Players",
    ],
)
