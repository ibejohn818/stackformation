==============
StackFormation
==============


.. image:: https://img.shields.io/pypi/v/stackformation.svg
        :target: https://pypi.python.org/pypi/stackformation

.. image:: https://img.shields.io/travis/ibejohn818/stackformation.svg
        :target: https://travis-ci.org/ibejohn818/stackformation

.. image:: https://readthedocs.org/projects/stackformation/badge/?version=latest
        :target: https://stackformation.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/ibejohn818/stackformation/shield.svg
     :target: https://pyup.io/repos/github/ibejohn818/stackformation/
     :alt: Updates


Stackfromation is an AWS CloudFormation framework that allows you to enforce "Infrastructure-as-code".
It uses a convention to allow you to manage your stack-resources as python objects.
It does not bind stacks together using Import and allows for more predictable updates to existing stacks
and quick prototyping of your infrastructure to different stages IE: DEV, STAGING & PRODUCTION.

Optionally, it also enforces an AMI workflow that separates the construction and updating of your AMI's
using ansible and packer.

* Free software: MIT license
* Documentation: https://stackformation.readthedocs.io.


Features
--------

* TODO

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

