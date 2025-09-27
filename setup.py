#!/usr/bin/env python3
"""
Setup script for Deepin Wallpaper Source Manager.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
else:
    requirements = [
        "PySide6>=6.4.0",
        "requests>=2.28.0",
        "Pillow>=9.0.0",
        "click>=8.0.0",
        "praw>=7.6.0",
        "openai>=1.0.0",
        "apify-client>=1.0.0",
        "imagehash>=4.3.0",
        "numpy>=1.21.0",
    ]

setup(
    name="deepin-wallpaper-source-manager",
    version="0.1.0",
    author="Deepin Community",
    author_email="community@deepin.org",
    description="A lightweight wallpaper downloader with AI generation capabilities for Deepin Desktop",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deepin-community/deepin-wallpaper-source-manager",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Desktop Environment",
        "Topic :: Multimedia :: Graphics",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "ai-local": [
            "diffusers>=0.21.0",
            "torch>=2.0.0",
            "transformers>=4.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "deepin-wallpaper-manager=ui.source_selector:main",
            "deepin-wallpaper-test=test_app:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)