#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="fuzzmon",
    version="0.4",
    packages=["fuzz_proxy"],
    author="Alex Moneger",
    author_email="alexmgr+github@gmail.com",
    description=(
        "A transport layer proxy which monitors the target server using ptrace"),
    license="MIT",
    keywords=["proxy", "fuzzing", "debugger", "ptrace", "bsd"],
    url="https://github.com/alexmgr/fuzzmon",
    install_requires=["python-ptrace", "distorm3"],
    scripts=["fuzzmon", "fuzzreplay"],
    # generate rst from .md:  pandoc --from=markdown --to=rst README.md -o README.rst
    long_description=read("README.rst") if os.path.isfile("README.rst") else read("README.md"),
    test_suite="nose.collector",
    tests_require=["nose"]
)
