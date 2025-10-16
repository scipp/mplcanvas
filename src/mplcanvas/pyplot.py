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

# # Global state (like matplotlib.pyplot)
# _current_figure: Optional[Figure] = None
# _current_axes: Optional[Axes] = None


# Figure management
def figure(**kwargs) -> Figure:
    """
    Create a new figure or retrieve an existing figure.

    Parameters match matplotlib.pyplot.figure()
    """

    return Figure(**kwargs)


def subplots(nrows=1, ncols=1, **kwargs):
    """
    Create a figure and subplots.

    Returns (fig, ax) or (fig, axes_array) to match matplotlib exactly.
    """
    # global _current_figure, _current_axes

    fig = figure(**kwargs)
    axes = []
    for i in range(nrows * ncols):
        ax = fig.add_subplot(nrows, ncols, i + 1)
        axes.append(ax)
    # print("axes", axes)
    return fig, np.array(axes) if nrows * ncols > 1 else axes[0]

    # if nrows == 1 and ncols == 1:
    #     ax = fig.mpl_figure.add_subplot(nrows, ncols, 1)
    #     # _current_axes = ax
    #     return fig, ax
    # else:
    #     # TODO: Implement multiple subplots
    #     raise NotImplementedError("Multiple subplots not yet implemented")
