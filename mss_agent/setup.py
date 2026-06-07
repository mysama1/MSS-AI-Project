from setuptools import setup, find_packages

setup(
    name="mss-agent",
    version="0.2.0",
    description="MSS-Agent: 世界上第一个内置'意义场自检'的开源 Agent 框架",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="MSS-AI Project",
    url="https://github.com/mysama1/MSS-AI-Project",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[],
    extras_require={
        "llm": ["openai>=1.0"],
        "dev": ["pytest", "black"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
