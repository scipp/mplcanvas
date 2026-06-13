# mplcanvas/figure.py
import pathlib

import anywidget
import ipywidgets as ipw
import matplotlib
import numpy as np
import traitlets
from matplotlib.axes import Axes
from matplotlib.colors import to_hex
from matplotlib.figure import Figure as MplFigure

matplotlib.use("Agg")


class Figure(anywidget.AnyWidget):
    """
    Top-level container for all plot elements using Anywidget for rendering.

    Uses matplotlib for layout and transformations, but renders with native
    browser canvas for better performance.
    """

    _esm = pathlib.Path(__file__).parent / "figure.js"
    _css = pathlib.Path(__file__).parent / "figure.css"

    # Widget dimensions
    width = traitlets.Int(600).tag(sync=True)
    height = traitlets.Int(400).tag(sync=True)

    # Number of canvas layers (one per axes + one for overlays)
    ncanvases = traitlets.Int(1).tag(sync=True)

    # Drawing commands sent to JavaScript
    draw_commands = traitlets.List([]).tag(sync=True)

    # Tool state (synced with JavaScript)
    active_tool = traitlets.Unicode("").tag(sync=True)  # "", "zoom", "pan"

    # Axis limits update from JavaScript
    axis_limits_update = traitlets.Dict({}).tag(sync=True)

    # Trigger for home button
    trigger_home = traitlets.Int(0).tag(sync=True)

    def __init__(self, ncanvases: int = 1, **kwargs):
        self.mpl_figure = MplFigure(**kwargs)

        # Convert figsize from inches to pixels
        self.figsize = self.mpl_figure.get_size_inches()
        self.dpi = self.mpl_figure.get_dpi()
        width = int(self.figsize[0] * self.dpi)
        height = int(self.figsize[1] * self.dpi)

        # Initialize the widget with explicit layout
        super().__init__(
            width=width,
            height=height,
            ncanvases=ncanvases + 1,
            layout=ipw.Layout(
                width=f"{width}px",
                height=f"{height}px",
            ),
        )

        # Canvas to axes mapping
        self._axes_to_canvas = {}
        self._canvas_to_axes = {}

        # Status bar
        self.status_bar = ipw.Label(value="")
        self.container = ipw.VBox([self, self.status_bar])

        # Listen for axis limit updates from JavaScript
        self.observe(self._on_axis_limits_update, names="axis_limits_update")
        self.observe(self._on_home_triggered, names="trigger_home")

    def add_subplot(self, nrows: int, ncols: int, index: int, **kwargs) -> Axes:
        new_axes = self.mpl_figure.add_subplot(nrows, ncols, index, **kwargs)
        canvas_index = index - 1
        self._axes_to_canvas[id(new_axes)] = canvas_index
        self._canvas_to_axes[canvas_index] = new_axes

        return new_axes

    @property
    def axes(self):
        """Return the list of axes in the figure"""
        return self.mpl_figure.axes

    @property
    def canvas(self):
        """Compatibility property - not used in anywidget version"""
        return self

    @property
    def drawing_canvas(self):
        """Compatibility property - not used in anywidget version"""
        return self

    @property
    def toolbar(self):
        """Compatibility property - not used in anywidget version"""
        return self

    def _repr_mimebundle_(self, include=None, exclude=None):
        """
        Jupyter representation - this makes the figure display automatically
        when it's the result of a cell.
        """
        self.draw()
        return self.container._repr_mimebundle_(include=include, exclude=exclude)

    def _on_axis_limits_update(self, change):
        """Handle axis limit updates from JavaScript (after zoom/pan)"""
        update = change["new"]
        if not update:
            return

        canvas_index = update.get("canvas_index")
        if canvas_index is None:
            return

        ax = self._canvas_to_axes.get(canvas_index)
        if ax is None:
            return

        # Update matplotlib axes limits
        xlim = update.get("xlim")
        ylim = update.get("ylim")
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)

        # Redraw the axes
        self.draw(ax=ax)

    def _on_home_triggered(self, change):
        """Handle home button clicks from JavaScript"""
        self.home()

    def home(self):
        """Reset all axes to their home (original) limits using matplotlib's autoscaling"""
        for ax in self._canvas_to_axes.values():
            ax.autoscale(enable=True, axis='both')  # Re-enable autoscaling
            ax.relim()  # Recalculate limits based on current data
            ax.autoscale_view()  # Apply the recalculated limits
        self.draw()

    def draw(self, ax: Axes | None = None):
        """
        Render the figure or a specific axes.

        If ax is None, redraw the entire figure.
        If ax is provided, redraw only that specific axes.
        """
        index = self._axes_to_canvas.get(id(ax)) if ax is not None else None

        if index is None:
            # Redraw all axes
            commands = []
            for i in range(len(self._canvas_to_axes)):
                ax = self._canvas_to_axes[i]
                commands.append(self._generate_draw_commands(ax, i))

            self.draw_commands = commands
        else:
            # Redraw specific axes
            commands = [self._generate_draw_commands(ax, index)]
            self.draw_commands = commands

    def _generate_draw_commands(self, ax: Axes, canvas_index: int) -> dict:
        """
        Generate drawing commands for a single axes.

        Returns a dictionary with all the drawing information needed by JavaScript.
        """
        # Get axis limits and transformation
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()

        # Transform limits to canvas coordinates
        (xmin_disp, ymin_disp), (xmax_disp, ymax_disp) = ax.transData.transform(
            ((xmin, ymin), (xmax, ymax))
        )
        width = xmax_disp - xmin_disp
        height = ymax_disp - ymin_disp

        commands = {
            "canvas_index": canvas_index,
            "limits": {
                "xmin": float(xmin),
                "xmax": float(xmax),
                "ymin": float(ymin),
                "ymax": float(ymax),
                "xmin_disp": float(xmin_disp),
                "ymin_disp": float(ymin_disp),
                "xmax_disp": float(xmax_disp),
                "ymax_disp": float(ymax_disp),
                "width": float(width),
                "height": float(height),
            },
            "lines": [],
            "collections": [],
            "frame": {
                "x": float(xmin_disp),
                "y": float(ymin_disp),
                "width": float(width),
                "height": float(height),
                "stroke_style": "black",
                "line_width": 1.0,
            },
            "ticks": self._generate_tick_commands(ax, xmin, xmax, ymin, ymax),
        }

        # Process all line artists
        for line in ax.lines:
            line_cmd = self._process_line(line, ax)
            if line_cmd is not None:
                commands["lines"].append(line_cmd)

        # Process all collections (scatter, etc.)
        for collection in ax.collections:
            collection_cmd = self._process_collection(
                collection, ax, xmin, xmax, ymin, ymax
            )
            if collection_cmd is not None:
                commands["collections"].append(collection_cmd)

        return commands

    def _process_line(self, line, ax) -> dict | None:
        """Convert a matplotlib Line2D to drawing commands"""
        xdata = line.get_xdata()
        ydata = line.get_ydata()

        if len(xdata) == 0 or len(ydata) == 0:
            return None

        # Transform to canvas coordinates
        points = ax.transData.transform(np.column_stack([xdata, ydata]))

        return {
            "type": "line",
            "points": points.tolist(),  # [[x1, y1], [x2, y2], ...]
            "stroke_style": to_hex(line.get_color()),
            "line_width": float(line.get_linewidth()),
        }

    def _process_collection(
        self, collection, ax, xmin, xmax, ymin, ymax
    ) -> dict | None:
        """Convert a matplotlib collection to drawing commands"""
        offsets = collection.get_offsets()
        if len(offsets) == 0:
            return None

        xdata, ydata = offsets[:, 0], offsets[:, 1]

        # Select only points within limits
        mask = (xdata >= xmin) & (xdata <= xmax) & (ydata >= ymin) & (ydata <= ymax)
        if mask.sum() == 0:
            return None

        xdata = xdata[mask]
        ydata = ydata[mask]

        # Transform to canvas coordinates
        points = ax.transData.transform(np.column_stack([xdata, ydata]))

        # Get marker size
        sizes = collection.get_sizes()
        if len(sizes) == 1:
            size = float((sizes[0] / np.pi) ** 0.5)
        else:
            size = float((sizes[mask][0] / np.pi) ** 0.5) if len(sizes) > 0 else 3.0

        # Determine marker type
        first_path = collection.get_paths()[0]
        marker_type = "square" if len(first_path.vertices) == 5 else "circle"

        return {
            "type": "collection",
            "points": points.tolist(),
            "fill_style": to_hex(collection.get_facecolor()[0]),
            "stroke_style": to_hex(collection.get_edgecolor()[0]),
            "size": size,
            "marker_type": marker_type,
        }

    def _generate_tick_commands(self, ax, xmin, xmax, ymin, ymax) -> dict:
        """Generate tick and label drawing commands"""
        tick_length = 6
        label_offset = 3

        xticks_data = []
        xticks = ax.get_xticks()
        xlabels = [lab.get_text() for lab in ax.get_xticklabels()]
        for tick, label in zip(xticks, xlabels, strict=False):
            if tick < xmin or tick > xmax:
                continue
            x, y = ax.transData.transform((tick, ymin))
            xticks_data.append({"x": float(x), "y": float(y), "label": label})

        yticks_data = []
        yticks = ax.get_yticks()
        ylabels = [lab.get_text() for lab in ax.get_yticklabels()]
        for tick, label in zip(yticks, ylabels, strict=False):
            if tick < ymin or tick > ymax:
                continue
            x, y = ax.transData.transform((xmin, tick))
            yticks_data.append({"x": float(x), "y": float(y), "label": label})

        xlabel = ax.xaxis.get_label()
        ylabel = ax.yaxis.get_label()

        xlabel_data = None
        if xlabel.get_text():
            x, y = ax.transAxes.transform(xlabel.get_position())
            xlabel_data = {
                "x": float(x),
                "y": float(self.height),
                "text": xlabel.get_text(),
            }

        ylabel_data = None
        if ylabel.get_text():
            x, y = ax.transAxes.transform(ylabel.get_position())
            ylabel_data = {"x": float(x), "y": float(y), "text": ylabel.get_text()}

        return {
            "tick_length": tick_length,
            "label_offset": label_offset,
            "xticks": xticks_data,
            "yticks": yticks_data,
            "xlabel": xlabel_data,
            "ylabel": ylabel_data,
        }
