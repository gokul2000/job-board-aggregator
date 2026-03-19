from setuptools import setup, find_packages

setup(
    name="jobhunt",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": ["jobhunt=jobhunt.cli:main"],
    },
    install_requires=[
        "requests>=2.28",
        "beautifulsoup4>=4.11",
        "lxml>=4.9",
    ],
    python_requires=">=3.10",
)
