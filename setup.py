import codecs
import os.path

from setuptools import find_packages, setup


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), "r") as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


def read_requirements(req_type=None):
    fname = f"requirements-{req_type}.txt" if req_type else "requirements.txt"
    with open(fname) as f:
        requires = (line.strip() for line in f)
        return [req for req in requires if req and not req.startswith("#")]


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="pyrfc-read",
    version=get_version("pyrfc_read/__init__.py"),
    author="Alex Marvin",
    author_email="alex.marvin@gmail.com",
    description="Read data from SAP R/3 Systems",
    url="https://github.com/amarvin/pyrfc-read",
    packages=find_packages(exclude=["tests"]),
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=read_requirements(),
    extras_require={
        "dev": read_requirements("dev"),
        "test": read_requirements("test"),
    },
)
