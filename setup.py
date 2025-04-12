from setuptools import setup, find_packages

setup(
    name="cmddocgen",
    version="0.1.0",
    description="CmdDocGen - Universal command line help information extraction and man page generation tool powered by LLM for intelligent subcommand analysis",
    author="Carlton",
    author_email="carlton2tang@gmail.com",
    url="https://github.com/2niuhe/CmdDocGen",
    packages=find_packages(),
    install_requires=["openai>=1.0.0", "python-dotenv>=0.20.0", "setuptools>=65.0.0"],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cmddocgen=cmddocgen.cli:main",
        ],
    },
    scripts=["cmddocgen/cli.py"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Documentation",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)
