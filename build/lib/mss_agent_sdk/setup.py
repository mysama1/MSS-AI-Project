"""
MSS-Agent SDK 安装脚本
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mss-agent-sdk",
    version="0.1.0",
    author="Redshift Tech",
    author_email="architect@redshift.tech",
    description="MSS-Agent SDK: 外挂式逻辑审计与意义锚定",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mysama1/MSS-AI-Project",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "mypy>=0.9",
        ],
    },
    entry_points={
        "console_scripts": [
            "mss-audit=mss_agent_sdk.cli:main",
        ],
    },
)
