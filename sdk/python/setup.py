from setuptools import setup, find_packages

setup(
    name="gnosis-sdk",
    version="0.1.0",
    description="Python SDK for the Gnosis AI Agent Platform",
    author="Gnosis Team",
    packages=find_packages(),
    install_requires=["httpx>=0.24"],
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
