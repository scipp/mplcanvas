# mplcanvas/pyplot.py
"""
mplcanvas.pyplot: Matplotlib-compatible plotting interface using ipycanvas

This module provides a matplotlib.pyplot compatible API that renders
to ipycanvas for better performance in Jupyter notebooks.

Usage:
    import mplcanvas.pyplot as plt

    x = [1, 2, 3, 4]
    y = [1, 4, 2, 3]
    plt.plot(x, y)
    plt.show()
"""

import numpy as np

from .figure import Figure


def figure(**kwargs) -> Figure:
    """
    Create a new figure.

    Parameters match matplotlib.pyplot.figure()
    """
    return Figure(**kwargs)


def subplots(nrows=1, ncols=1, **kwargs):
    """
    Create a figure and subplots.

    Returns (fig, ax) or (fig, axes_array) to match matplotlib exactly.
    """
    prod = nrows * ncols
    fig = figure(ncanvases=prod, **kwargs)
    axes = []
    for i in range(prod):
        ax = fig.add_subplot(nrows, ncols, i + 1)
        axes.append(ax)
    return fig, np.array(axes) if prod > 1 else axes[0]
