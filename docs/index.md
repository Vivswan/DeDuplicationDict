# Welcome to DeDuplicationDict's documentation!

GitHub: [https://github.com/Vivswan/DeDuplicationDict](https://github.com/Vivswan/DeDuplicationDict)

[![PyPI version](https://badge.fury.io/py/deduplicationdict.svg)](https://badge.fury.io/py/deduplicationdict)
[![Documentation Status](https://readthedocs.org/projects/deduplicationdict/badge/?version=stable)](https://deduplicationdict.readthedocs.io/en/stable/?badge=stable)
[![Python](https://img.shields.io/badge/python-3.7--3.10-blue)](https://badge.fury.io/py/deduplicationdict)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-blue.svg)](https://opensource.org/licenses/MPL-2.0)

A dictionary-like class that deduplicates values by storing them in a separate dictionary and replacing
them with their corresponding hash values. This class is particularly useful for large dictionaries with
repetitive entries, as it can save memory by storing values only once and substituting recurring values
with their hash representations.

This class supports nested structures by automatically converting nested dictionaries into
`DeDuplicationDict` instances. It also provides various conversion methods to convert between regular
dictionaries and `DeDuplicationDict` instances.

## Table of contents

```{toctree}
:maxdepth: 2

install
autoapi/index
changelog

```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
