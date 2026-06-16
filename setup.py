from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_desc = f.read()

setup(
    name="mss-agent",
    version="0.3.0",
    description="MSS-Agent: 内置意义场自检 + 流式呼吸感 + 本地加密保险箱的开源Agent框架",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="MSS-AI Project",
    url="https://github.com/mysama1/MSS-AI-Project",
    license="MIT",
    packages=find_packages(include=["mss_agent", "mss_agent.*", "mssclaw", "mssclaw.*"]),
    entry_points={
        "console_scripts": [
            "mss-agent=mss_agent.cli:main",
            "mss-vault=mss_agent.vault_cli:main",
            "mss-agent-serve=mss_agent.agent_serve:main",
            "mssclaw=mssclaw.cli:main",
        ],
    },
    python_requires=">=3.10",
    install_requires=["requests>=2.28", "cryptography>=41.0"],
    extras_require={
        "llm": ["openai>=1.0"],
        "dev": ["pytest", "pytest-cov"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
