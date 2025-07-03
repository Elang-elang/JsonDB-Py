from setuptools import setup, find_packages

setup(
    name="jsondb-python",
    version="1.0.5",
    author="Elang Muhammad",
    author_email="elangmuhammad888@gmail.com",
    description="A simple, lightweight, and file-based JSON database library for Python.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Elang-elang/JsonDB",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Database",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    keywords=["json", "database", "file-based", "nosql", "db"],
    entry_points={
        "console_scripts": [
            "jsondb=jsondb.cli:main",
        ],
    },
)
