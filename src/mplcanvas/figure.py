# mplcanvas/figure.py
from contextlib import nullcontext

import ipywidgets as ipw
import matplotlib
from ipycanvas import MultiCanvas, hold_canvas
from matplotlib.axes import Axes
from matplotlib.figure import Figure as MplFigure

from .render import draw_axes
from .toolbar import Toolbar

matplotlib.use("Agg")


class Figure(ipw.HBox):
    """
    Top-level container for all plot elements.

    Inherits from VBox so it can be composed with other widgets,
    and implements _repr_mimebundle_ for automatic Jupyter display.
    """

    def __init__(self, ncanvases: int = 1, **kwargs):
        self.mpl_figure = MplFigure(**kwargs)

        # Convert figsize from inches to pixels
        self.figsize = self.mpl_figure.get_size_inches()
        self.dpi = self.mpl_figure.get_dpi()
        self.width = int(self.figsize[0] * self.dpi)
        self.height = int(self.figsize[1] * self.dpi)

        layout = ipw.Layout(width=f"{self.width}px", height=f"{self.height}px")

        # Create the canvas: one per axes plus one for drawing overlays
        self.canvas = MultiCanvas(
            ncanvases + 1, width=self.width, height=self.height, layout=layout
        )
        self.drawing_canvas = self.canvas[-1]

        self.toolbar = Toolbar(figure=self)
        self.status_bar = ipw.Label(value="")

        super().__init__(
            children=[self.toolbar, ipw.VBox([self.canvas, self.status_bar])], **kwargs
        )

        # Canvas to axes mapping
        self._axes_to_canvas = {}
        self._canvas_to_axes = {}

    def add_subplot(self, nrows: int, ncols: int, index: int, **kwargs) -> Axes:
        new_axes = self.mpl_figure.add_subplot(nrows, ncols, index, **kwargs)
        self._axes_to_canvas[id(new_axes)] = index - 1
        self._canvas_to_axes[index - 1] = new_axes
        return new_axes

    @property
    def axes(self):
        """Return the list of axes in the figure"""
        return self.mpl_figure.axes

    def _find_axes_at_position(self, xy: tuple[float, float]) -> Axes | None:
        """Find which axes (if any) contains the given canvas coordinates"""
        for ax in self.axes:
            if ax.contains_point(xy):
                return ax

    def _repr_mimebundle_(self, include=None, exclude=None):
        """
        Jupyter representation - this makes the figure display automatically
        when it's the result of a cell.
        """
        self.draw()
        return super()._repr_mimebundle_(include=include, exclude=exclude)

    def _draw_canvas(self, canvas, index, hold=True):
        """Render the entire figure"""
        ctx = hold_canvas(canvas) if hold else nullcontext()
        with ctx:
            canvas.clear()
            ax = self._canvas_to_axes[index]
            draw_axes(ax, canvas)

    def draw(self, ax: Axes | None = None):
        """
        Render the figure or a specific axes.

        If index is None, redraw the entire figure.
        If index is an integer, redraw only the specified axes (1-based index).
        """
        index = self._axes_to_canvas.get(id(ax)) if ax is not None else None
        if index is None:
            # Redraw all canvases
            with hold_canvas(self.canvas):
                for i in range(len(self.canvas._canvases) - 1):
                    self._draw_canvas(self.canvas[i], index=i, hold=False)
        else:
            self._draw_canvas(self.canvas[index], index=index)
