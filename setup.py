"""
MSS-AI Setup Script
Meta-Self-Similarity System AI - Installation Configuration
"""

from setuptools import setup, find_packages
import os

# Read README
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()

# Read requirements
requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
install_requires = []
if os.path.exists(requirements_path):
    with open(requirements_path, 'r', encoding='utf-8') as f:
        install_requires = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#') and not line.startswith('Optional')
        ]

setup(
    name="mss-ai",
    version="1.0.0",
    author="MSS Research Initiative",
    author_email="research@mss-ai.org",
    description="Meta-Self-Similarity System AI - Symbolic Reasoning Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mysama1/MSS-AI-Project",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
        ],
        "perf": [
            "numba>=0.58.0",
        ],
        "viz": [
            "matplotlib>=3.8.0",
            "plotly>=5.18.0",
        ],
        "all": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
            "numba>=0.58.0",
            "matplotlib>=3.8.0",
            "plotly>=5.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mss-ai-cli=interactive_cli:main",
            "mss-ai-api=web_api:main",
            "mss-ai-sim=simulation_framework:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.jsonl", "*.json", "*.md", "*.txt"],
    },
    zip_safe=False,
)
