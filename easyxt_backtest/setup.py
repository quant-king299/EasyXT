#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for easyxt_backtest
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="easyxt-backtest",
    version="0.2.0",
    author="MiniQMT Team",
    author_email="noreply@example.com",
    description="Universal backtesting framework for quantitative trading strategies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quant-king299/EasyXT",
    packages=["easyxt_backtest"],
    package_dir={'easyxt_backtest': '.'},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "requests>=2.25.0",
    ],
    project_urls={
        "Homepage": "https://github.com/quant-king299/EasyXT",
        "Source": "https://github.com/quant-king299/EasyXT",
        "Documentation": "https://github.com/quant-king299/EasyXT/blob/main/easyxt_backtest/README.md",
    },
)
