#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
import sys
if sys.version_info < (3, 0):
    sys.exit('Sorry, Only Python 3.x is not supported')

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

with open('requirements.txt', 'r') as req:
    requirements = [line.strip() for line in req]

with open('requirements_dev.txt', 'r') as req:
    test_requirements = [line.strip() for line in req]

setup_requirements = [
    'pytest-runner',
    # TODO(ibejohn818): put setup requirements (distutils extensions, etc.)
    # here
]


setup(
    name='jh-stackformation',
    version='0.2.35',
    description="AWS CloudFormation framework",
    long_description=readme + '\n\n' + history,
    author="John Hardy",
    author_email='john@johnchardy.com',
    url='https://github.com/ibejohn818/stackformation',
    # packages=find_packages(include=['stackformation']),
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'stackformation=stackformation.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='stackformation',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
