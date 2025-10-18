import numpy as np

import mplcanvas.pyplot as plt


def test_plot_one_line():
    fig, ax = plt.subplots()
    points_per_line = 100
    x = np.linspace(0, 10, points_per_line)
    y = np.sin(x) * np.exp(-x / 5) + np.random.uniform(-0.1, 0.1, size=points_per_line)
    ax.plot(x, y)

    fig.draw()

    assert len(fig.axes) == 1
    assert fig.canvas is not None
    assert fig.drawing_canvas is not None
    assert fig.toolbar is not None
    assert fig.status_bar is not None


def test_plot_multiple_lines():
    fig, ax = plt.subplots()
    points_per_line = 100
    x = np.linspace(0, 10, points_per_line)
    for i in range(4):
        y = np.sin(x + i) * np.exp(-x / 5) + np.random.uniform(
            -0.1, 0.1, size=points_per_line
        )
        ax.plot(x, y)

    fig.draw()

    assert len(fig.axes) == 1
    assert len(ax.lines) == 4
    assert fig.canvas is not None
    assert fig.drawing_canvas is not None
    assert fig.toolbar is not None
    assert fig.status_bar is not None


def test_subplots():
    fig, axs = plt.subplots(1, 2)
    points_per_line = 100
    x = np.linspace(0, 10, points_per_line)
    for i, ax in enumerate(axs.flat):
        y = np.sin(x + i) * np.exp(-x / 5) + np.random.uniform(
            -0.1, 0.1, size=points_per_line
        )
        ax.plot(x, y)

    fig.draw()

    assert len(fig.axes) == 2
    assert len(axs[0].lines) == 1
    assert len(axs[1].lines) == 1
    assert fig.canvas is not None
    assert fig.drawing_canvas is not None
    assert fig.toolbar is not None
    assert fig.status_bar is not None


def test_scatter():
    fig, ax = plt.subplots()
    x, y = np.random.normal(size=(2, 1000))
    ax.scatter(x, y, marker='o')

    fig.draw()

    assert len(fig.axes) == 1
    assert len(ax.collections) == 1
    assert fig.canvas is not None
    assert fig.drawing_canvas is not None
    assert fig.toolbar is not None
    assert fig.status_bar is not None
