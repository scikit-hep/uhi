# UHI


[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![Code style: black][black-badge]][black-link]

[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]
[![Gitter][gitter-badge]][gitter-link]
[![Scikit-HEP][sk-badge]](https://scikit-hep.org/)


This is a package meant primarily for [documenting][rtd-link] histogram indexing and the PlottableProtocol and any future cross-library standards. It also contains the code for the PlottableProtocol, to be used in type checking libraries wanting to conform to the protocol. Eventually, it might gain a set of tools for testing conformance to UHI indexing, as well. It is not currently intended to be a runtime dependency, but only a type checking, testing, and/or docs dependency in support of other libraries (such as [boost-histogram][], [hist][], [mplhep][], [uproot4][], and eventually [histoprint][]). It requires Python 3.6+.


[actions-badge]:            https://github.com/Scikit-HEP/uhi/workflows/CI/badge.svg
[actions-link]:             https://github.com/Scikit-HEP/uhi/actions
[black-badge]:              https://img.shields.io/badge/code%20style-black-000000.svg
[black-link]:               https://github.com/psf/black
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/uhi
[conda-link]:               https://github.com/conda-forge/uhi-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/Scikit-HEP/uhi/discussions
[gitter-badge]:             https://badges.gitter.im/https://github.com/Scikit-HEP/uhi/community.svg
[gitter-link]:              https://gitter.im/https://github.com/Scikit-HEP/uhi/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge
[pypi-link]:                https://pypi.org/project/uhi/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/uhi
[pypi-version]:             https://badge.fury.io/py/uhi.svg
[rtd-badge]:                https://readthedocs.org/projects/uhi/badge/?version=latest
[rtd-link]:                 https://uhi.readthedocs.io/en/latest/?badge=latest
[sk-badge]:                 https://scikit-hep.org/assets/images/Scikit--HEP-Project-blue.svg

[boost-histogram]:          https://github.com/scikit-hep/boost-histogram
[hist]:                     https://github.com/scikit-hep/hist
[mplhep]:                   https://github.com/scikit-hep/mplhep
[uproot4]:                  https://github.com/scikit-hep/uproot4
[histoprint]:               https://github.com/scikit-hep/histoprint
