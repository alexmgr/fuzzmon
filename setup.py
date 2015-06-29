#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="fuzz-proxy",
    version="0.1",
    packages=["fuzz_proxy"],
    author="Alex Moneger",
    author_email="alexmgr+github@gmail.com",
    description=(
        "A transport layer proxy which monitors the server backend"),
    license="GPLv2",
    keywords=["proxy", "fuzzing", "debugger"],
    url="https://github.com/alexmgr/fuzz-proxy",
    install_requires=["python-ptrace"],
    test_suite="nose.collector",
    tests_require=["nose"]
)