from setuptools import setup, find_packages

setup(
    name="cmddocgen",
    version="0.1.0",
    author="Carlton Tang",
    author_email="carlton2tang@gmail.com",
    url="https://github.com/2niuhe/CmdDocGen",
    packages=find_packages(include=['cmddocgen', 'cmddocgen.*']),
    include_package_data=True,
    package_data={
        '': ['*.txt', '*.md', '*.json', '*.env'],
    },
    install_requires=[
        "openai>=1.0.0", 
        "python-dotenv>=0.20.0",
        "setuptools>=65.0.0"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cmddocgen=cmddocgen.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Documentation",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)