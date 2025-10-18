# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 Scipp contributors (https://github.com/scipp)
# ruff: noqa: E402, F401, I

import importlib.metadata

try:
    __version__ = importlib.metadata.version(__package__ or __name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"


# For matplotlib compatibility
import matplotlib.rcsetup as _rcsetup

from . import pyplot
from .figure import Figure

rcParams = _rcsetup.defaultParams.copy()

# Re-export pyplot functions at package level (like matplotlib)
from .pyplot import (
    figure,
    subplots,
)

__all__ = [
    "Figure",
    "figure",
    "pyplot",
    "rcParams",
    "subplots",
]


del importlib
