"""
Navigation toolbar for mplcanvas - operates on any axes in the figure
"""

import ipywidgets as ipw
from ipycanvas import hold_canvas

from .utils import flip_y


class Toolbar(ipw.VBox):
    """
    Navigation toolbar that can operate on any axes in the figure.

    Similar to matplotlib's NavigationToolbar2 - activates tools that work
    on whichever axes the user interacts with.
    """

    def __init__(self, figure, **kwargs):
        self.figure = figure

        # Tool state
        self._active_tool = None  # 'zoom', 'pan', or None
        self._pan_info = None
        self._zoom_info = None
        self._active_axes = None  # Which axes is currently being interacted with
        self._tools_lock = False

        button_layout = ipw.Layout(width="37px", padding="0px 0px 0px 0px")

        # Home button
        self.home_button = ipw.Button(
            icon="home",
            tooltip="Reset all axes to home view",
            layout=button_layout,
        )
        self.home_button.on_click(self._on_home_clicked)

        # Pan button
        self.pan_button = ipw.ToggleButton(
            icon="arrows",
            tooltip="Pan tool - drag to move any plot",
            layout=button_layout,
        )
        self.pan_button.observe(self._on_pan_clicked, names="value")

        # Zoom button
        self.zoom_button = ipw.ToggleButton(
            icon="square-o",
            tooltip="Zoom tool - drag to select zoom region on any plot",
            layout=button_layout,
        )
        self.zoom_button.observe(self._on_zoom_clicked, names="value")

        self.tools = {
            "home": self.home_button,
            "pan": self.pan_button,
            "zoom": self.zoom_button,
        }

        self._setup_event_connections()

        super().__init__(
            children=list(self.tools.values()),
            layout=ipw.Layout(width="auto"),
            **kwargs,
        )

    def _on_home_clicked(self, button):
        """Reset all axes to home view"""
        for ax in self.figure.axes:
            ax.autoscale()
        self.figure.draw()

    def _on_pan_clicked(self, change):
        """Activate/deactivate pan tool"""
        if self._tools_lock:
            return
        self._tools_lock = True
        if change["new"]:
            self._active_tool = "pan"
            self.zoom_button.value = False  # Deactivate zoom if active
        else:
            if self._active_tool == "pan":
                self._active_tool = None
        self._tools_lock = False

    def _on_zoom_clicked(self, change):
        """Activate/deactivate zoom tool"""
        if self._tools_lock:
            return
        self._tools_lock = True
        if change["new"]:
            self._active_tool = "zoom"
            self.pan_button.value = False  # Deactivate pan if active
        else:
            if self._active_tool == "zoom":
                self._active_tool = None
        self._tools_lock = False

    def _setup_event_connections(self):
        self.figure.canvas.on_mouse_down(self._on_canvas_mouse_down)
        self.figure.canvas.on_mouse_up(self._on_canvas_mouse_up)
        self.figure.canvas.on_mouse_move(self._on_canvas_mouse_move)

    def _on_canvas_mouse_move(self, x: float, y: float):
        """Handle canvas mouse move events"""
        # Always track mouse position for cursor display
        canvas_y = y
        y = flip_y(y, self.figure.canvas)
        if self._active_axes is None:
            ax = self.figure._find_axes_at_position((x, y))
            if ax is None:
                self.figure.status_bar.value = ""
                return
        else:
            ax = self._active_axes

        inv = ax.transData.inverted()
        data_x, data_y = inv.transform((x, y))
        self.figure.status_bar.value = f"Mouse at ({data_x:.1f}, {data_y:.1f})"

        if self._active_tool == "pan":
            self._do_pan(x, y)
        elif self._active_tool == "zoom" and self._zoom_info is not None:
            self._update_zoom_preview(x, canvas_y)

    def _on_canvas_mouse_down(self, x: float, y: float):
        """Handle mouse press for active tools"""
        canvas_y = y
        y = flip_y(y, self.figure.canvas)
        self._active_axes = self.figure._find_axes_at_position((x, y))
        if (self._active_axes is None) or (self._active_tool is None):
            return

        if self._active_tool == "pan":
            self._start_pan(x, y)
        elif self._active_tool == "zoom":
            self._start_zoom(x, canvas_y)

    def _on_canvas_mouse_up(self, x: float, y: float):
        if self._active_tool == "pan" and self._pan_info is not None:
            self._end_pan()
        elif self._active_tool == "zoom":
            self._end_zoom(x, y)

    def _start_pan(self, x, y):
        """Start panning operation on the active axes"""

        ax = self._active_axes
        xlim, ylim = ax.get_xlim(), ax.get_ylim()

        xy_canvas = ax.transData.transform(((xlim[0], ylim[0]), (xlim[1], ylim[1])))
        xlim_canvas = (xy_canvas[0][0], xy_canvas[1][0])
        ylim_canvas = (xy_canvas[0][1], xy_canvas[1][1])

        self._pan_info = {
            "origin": (x, y),
            "limits": (xlim, ylim),
            "scale": (
                (xlim[1] - xlim[0]) / (xlim_canvas[1] - xlim_canvas[0]),
                (ylim[1] - ylim[0]) / (ylim_canvas[1] - ylim_canvas[0]),
            ),
        }

    def _do_pan(self, x, y):
        if self._pan_info is None:
            return

        ax = self._active_axes

        dx = (x - self._pan_info["origin"][0]) * self._pan_info["scale"][0]
        dy = (y - self._pan_info["origin"][1]) * self._pan_info["scale"][1]

        # Apply pan using original limits as reference
        start_xlim, start_ylim = self._pan_info["limits"]
        new_xlim = (start_xlim[0] - dx, start_xlim[1] - dx)
        new_ylim = (start_ylim[0] - dy, start_ylim[1] - dy)

        # Update limits and redraw
        ax.set(xlim=new_xlim, ylim=new_ylim)
        self.figure.draw(ax=ax)

    def _end_pan(self):
        """End panning operation"""
        self._pan_info = None
        self._active_axes = None

    def _start_zoom(self, x, y):
        """Start zoom selection on the active axes"""
        ax = self._active_axes
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        # Convert limits to canvas coordinates
        (xmin_canvas, ymin_canvas), (xmax_canvas, ymax_canvas) = ax.transData.transform(
            ((xlim[0], ylim[0]), (xlim[1], ylim[1]))
        )
        self._zoom_info = {
            "origin": (x, y),
            "xmin": xmin_canvas,
            "xmax": xmax_canvas,
            "ymin": ymin_canvas,
            "ymax": ymax_canvas,
        }

    def _update_zoom_preview(self, x: float, y: float):
        """Optimized zoom rectangle with minimal redraw"""
        if self._zoom_info is None or self._active_axes is None:
            return
        # Use the same pattern as pure ipycanvas example
        canvas = self.figure.drawing_canvas

        # Add zoom rectangle
        x1, y1 = self._zoom_info["origin"]
        x2, y2 = x, y

        x2 = max(self._zoom_info["xmin"], min(self._zoom_info["xmax"], x2))
        y2 = max(self._zoom_info["ymin"], min(self._zoom_info["ymax"], y2))

        # Calculate rectangle coordinates
        rect_x = min(x1, x2)
        rect_y = min(y1, y2)
        rect_width = abs(x2 - x1)
        rect_height = abs(y2 - y1)
        self._zoom_info["rectangle"] = (rect_x, rect_y, rect_width, rect_height)

        with hold_canvas(canvas):
            canvas.clear()

            # Set rectangle style
            canvas.stroke_style = "black"
            canvas.line_width = 1

            # Draw rectangle border
            canvas.stroke_rect(*self._zoom_info["rectangle"])

    def _end_zoom(self, x, y):
        """Complete zoom operation on the active axes"""
        self.figure.drawing_canvas.clear()

        # Ensure we have a proper rectangle (not just a click)
        min_size = 1  # Minimum zoom region size
        if (
            self._zoom_info["rectangle"][2] < min_size
            or self._zoom_info["rectangle"][3] < min_size
        ):
            self._zoom_info = None
            self._active_axes = None
            return

        index = self.figure._axes_to_canvas[id(self._active_axes)]
        canvas = self.figure.canvas[index]

        # Set new limits on the active axes
        # Convert rectangle corners back to data coordinates
        x1 = min(self._zoom_info["origin"][0], x)
        y1 = min(self._zoom_info["origin"][1], y)
        x2, y2 = (
            x1 + self._zoom_info["rectangle"][2],
            y1 + self._zoom_info["rectangle"][3],
        )
        inv = self._active_axes.transData.inverted()
        (xdata_1, ydata_1), (xdata_2, ydata_2) = inv.transform(
            [(x1, flip_y(y1, canvas)), (x2, flip_y(y2, canvas))]
        )

        self._active_axes.set_xlim(sorted([xdata_1, xdata_2]))
        self._active_axes.set_ylim(sorted([ydata_1, ydata_2]))

        self.figure.draw(ax=self._active_axes)  # Final draw to ensure clean state
        self._zoom_info = None
        self._active_axes = None
