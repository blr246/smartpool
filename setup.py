import os
from setuptools import find_packages, setup


def read(fname):
    """ Read a file relative to this script's path. """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="smartpool",
    version="0.1",
    author="Brandon L. Reiss",
    author_email="brandon@brandonreiss.com",
    description="A library for resource pooling in Python",
    license="MIT",
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=[dep for dep in
                      read('requirements.txt').split('\n')
                      if dep][:-1],
    long_description=read('README'),
)
