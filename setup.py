#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="fuzzmon",
    version="0.2",
    packages=["fuzz_proxy"],
    author="Alex Moneger",
    author_email="alexmgr+github@gmail.com",
    description=(
        "A transport layer proxy which monitors the target server using ptrace"),
    license="GPLv2",
    keywords=["proxy", "fuzzing", "debugger", "ptrace", "bsd"],
    url="https://github.com/alexmgr/fuzzmon",
    install_requires=["python-ptrace", "distorm3"],
    scripts=["fuzzmon"],
    test_suite="nose.collector",
    tests_require=["nose"]
)
