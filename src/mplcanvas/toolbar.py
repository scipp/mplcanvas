# mplcanvas/widgets/toolbar.py
"""
Navigation toolbar for mplcanvas - operates on any axes in the figure
"""

import ipywidgets as widgets
from ipycanvas import hold_canvas

from .utils import flip_y


class Toolbar(widgets.VBox):
    """
    Navigation toolbar that can operate on any axes in the figure.

    Similar to matplotlib's NavigationToolbar2 - activates tools that work
    on whichever axes the user interacts with.
    """

    def __init__(self, figure, **kwargs):
        self.figure = figure

        # Tool state
        self._active_tool = None  # 'zoom', 'pan', or None
        self._zoom_rect_start = None
        # self._pan_start_canvas = None
        self._pan_start = None
        self._pan_start_point = None
        self._pan_start_limits = None
        self._active_axes = None  # Which axes is currently being interacted with
        self._tools_lock = False

        # Store home views for all axes (will be populated as axes are added)
        self._home_views = {}  # {axes_id: (xlim, ylim)}

        # Zoom rectangle state
        self._zoom_rect_start = None
        self._zoom_rect_current = None
        self._zoom_rect_visible = False

        button_layout = widgets.Layout(width="37px", padding="0px 0px 0px 0px")

        # Home button
        self.home_button = widgets.Button(
            # description="🏠",
            icon="home",
            tooltip="Reset all axes to home view",
            # style=button_style,
            layout=button_layout,
        )
        self.home_button.on_click(self._on_home_clicked)

        # Pan button
        self.pan_button = widgets.ToggleButton(
            icon="arrows",
            tooltip="Pan tool - drag to move any plot",
            # style=button_style,
            layout=button_layout,
        )
        self.pan_button.observe(self._on_pan_clicked, names="value")

        # Zoom button
        self.zoom_button = widgets.ToggleButton(
            icon="square-o",
            tooltip="Zoom tool - drag to select zoom region on any plot",
            # style=button_style,
            layout=button_layout,
        )
        self.zoom_button.observe(self._on_zoom_clicked, names="value")

        self.tools = {
            "home": self.home_button,
            "pan": self.pan_button,
            "zoom": self.zoom_button,
        }

        # Set up event connections - we'll connect to all axes
        self._setup_event_connections()

        # Initialize as VBox
        super().__init__(
            children=list(self.tools.values()),
            layout=widgets.Layout(width="auto"),
            **kwargs,
        )

    # Button event handlers
    def _on_home_clicked(self, button):
        """Reset all axes to home view"""
        for ax in self.figure.axes:
            ax.autoscale_view()

            # axes_id = id(axes)
            # if axes_id in self._home_views:
            #     xlim, ylim = self._home_views[axes_id]
            #     axes.set_xlim(*xlim)
            #     axes.set_ylim(*ylim)

        # self.status_label.value = "Reset all axes to home view"
        # self._active_tool = None
        # self._update_button_states()
        self.figure.draw()

    def _on_pan_clicked(self, change):
        """Activate/deactivate pan tool"""
        if self._tools_lock:
            return
        self._tools_lock = True
        if change["new"]:  # Button toggled on
            self._active_tool = "pan"
            self.zoom_button.value = False  # Deactivate zoom if active
            # self.status_label.value = "Pan tool active - drag on any plot to move it"
        else:  # Button toggled off
            if self._active_tool == "pan":
                self._active_tool = None
                # self.status_label.value = "Pan tool deactivated"
        # if self._active_tool == "pan":
        #     self._active_tool = None
        #     # self.status_label.value = "Pan tool deactivated"
        # else:
        #     self._active_tool = "pan"
        #     # self.status_label.value = "Pan tool active - drag on any plot to move it"
        # self._update_button_states()
        self._tools_lock = False

    def _on_zoom_clicked(self, change):
        """Activate/deactivate zoom tool"""
        if self._tools_lock:
            return
        self._tools_lock = True
        if change["new"]:  # Button toggled on
            self._active_tool = "zoom"
            self.pan_button.value = False  # Deactivate pan if active
            self._clear_zoom_rectangle()  # Clear any active rectangle

            # self.status_label.value = (
            #     "Zoom tool active - drag on any plot to select region"
            # )
        else:  # Button toggled off
            if self._active_tool == "zoom":
                self._active_tool = None
                # self.status_label.value = "Zoom tool deactivated"
        self._tools_lock = False
        # if self._active_tool == "zoom":
        #     self._active_tool = None
        #     # self.status_label.value = "Zoom tool deactivated"
        # else:
        #     self._active_tool = "zoom"
        #     # self.status_label.value = (
        #     #     "Zoom tool active - drag on any plot to select region"
        #     # )
        # self._update_button_states()

    def _store_home_view(self, axes):
        """Store the current view of an axes as its home view"""
        axes_id = id(axes)
        self._home_views[axes_id] = (axes.get_xlim(), axes.get_ylim())

    def _setup_event_connections(self):
        # """Connect to all existing axes in the figure"""
        # for axes in self.figure.axes:
        #     self.add_axes(axes)
        self.figure.canvas.on_mouse_down(self._on_canvas_mouse_down)
        self.figure.canvas.on_mouse_up(self._on_canvas_mouse_up)
        self.figure.canvas.on_mouse_move(self._on_canvas_mouse_move)

    def _on_canvas_mouse_move(self, x: float, y: float):
        """Handle canvas mouse move events"""
        # Always track mouse position for cursor display
        # self._current_mouse_pos = (x, y)
        y = flip_y(y, self.figure.canvas)
        ax = self.figure._find_axes_at_position((x, y))
        if ax is None:
            self.figure.status_bar.value = ""
            return

        inv = ax.transData.inverted()
        data_x, data_y = inv.transform((x, y))
        self.figure.status_bar.value = f"Mouse at ({data_x:.1f}, {data_y:.1f})"

        if self._active_tool == "pan":
            # self._do_pan(ax, data_x, data_y)
            self._do_pan(ax, x, y)

    def _on_canvas_mouse_down(self, x: float, y: float):
        """Handle mouse press for active tools"""
        y = flip_y(y, self.figure.canvas)
        ax = self.figure._find_axes_at_position((x, y))
        if ax is None:
            return

        if self._active_tool == "pan":
            # self._active_axes = self._determine_active_axes(event)
            # if self._active_axes:
            self._start_pan(ax, x, y)
        elif self._get_active_tool() == "zoom":
            # self._active_axes = self._determine_active_axes(event)
            self._start_zoom(ax, x, y)

        # if not self._point_in_axes(x, y):
        #     return

    def _on_canvas_mouse_up(self, x: float, y: float):
        if self._active_tool == "pan" and self._pan_start is not None:
            self._end_pan()

    # In toolbar _start_pan:
    def _start_pan(self, ax, x, y):
        """Start panning operation on the active axes"""

        # inv = ax.transData.inverted()
        # data_x, data_y = inv.transform((x, y))
        # self._pan_start_point = (data_x, data_y)
        xlim, ylim = ax.get_xlim(), ax.get_ylim()

        xy_canvas = ax.transData.transform(((xlim[0], ylim[0]), (xlim[1], ylim[1])))
        xlim_canvas = (xy_canvas[0][0], xy_canvas[1][0])
        ylim_canvas = (xy_canvas[0][1], xy_canvas[1][1])

        self._pan_start = {
            "origin": (x, y),
            "limits": (xlim, ylim),
            "scale": (
                (xlim[1] - xlim[0]) / (xlim_canvas[1] - xlim_canvas[0]),
                (ylim[1] - ylim[0]) / (ylim_canvas[1] - ylim_canvas[0]),
            ),
        }

        # self._pan_start_limits = (ax.get_xlim(), ax.get_ylim())
        # print("self._pan_start_point", self._pan_start_point)

    # def _do_pan(self, ax, data_x, data_y):
    def _do_pan(self, ax, x, y):
        # """Perform panning using canvas coordinate deltas"""
        # print(self._pan_start_canvas, self._pan_start_limits, self._active_axes)
        if (
            self._pan_start is None
            # or self._pan_start_limits is None
            # or self._active_axes is None
        ):
            return

        dx = (x - self._pan_start["origin"][0]) * self._pan_start["scale"][0]
        dy = (y - self._pan_start["origin"][1]) * self._pan_start["scale"][1]

        # Apply pan using original limits as reference
        start_xlim, start_ylim = self._pan_start["limits"]

        # print("start point", self._pan_start_point)
        # print("data point", (data_x, data_y))
        # print("delta", (dx, dy))
        # print("start limits", self._pan_start_limits)

        new_xlim = (start_xlim[0] - dx, start_xlim[1] - dx)
        new_ylim = (start_ylim[0] - dy, start_ylim[1] - dy)
        # print("new limits", new_xlim, new_ylim)

        # Update limits and redraw
        ax.set(xlim=new_xlim, ylim=new_ylim)
        # self.figure.mpl_figure.canvas.draw_idle()
        self.figure.draw()

    def _end_pan(self):
        """End panning operation"""
        self._pan_start = None
        # self._pan_start_limits = None
        # self._active_axes = None

    def _start_zoom(self, ax, x, y):
        """Start zoom selection on the active axes"""
        self._zoom_rect_start = (x, y)

    # def _get_active_tool(self):
    #     """Return the currently active tool"""
    #     for name, tool in self.tools.items():
    #         if getattr(tool, "value", False):
    #             return name
    #     return None

    # Mouse event handlers
    def _on_mouse_move(self, event):
        """Handle mouse movement for active tools"""
        if self._active_tool == "pan" and self._pan_start_canvas is not None:
            # Continue pan on the same axes we started on
            if self._active_axes == event.inaxes:
                self._do_pan(event)
        elif self._active_tool == "zoom" and self._zoom_rect_start is not None:
            # Continue zoom on the same axes we started on
            if self._active_axes == event.inaxes:
                self._update_zoom_preview(event)

    def _on_mouse_press(self, event):
        """Handle mouse press for active tools"""
        if self._active_tool == "pan":
            self._active_axes = self._determine_active_axes(event)
            if self._active_axes:
                self._start_pan(event)
        elif self._active_tool == "zoom":
            self._active_axes = self._determine_active_axes(event)
            if self._active_axes:
                self._start_zoom(event)

    def _on_mouse_release(self, event):
        """Handle mouse release for active tools"""
        if self._active_tool == "pan" and self._pan_start_canvas is not None:
            if self._active_axes == self._determine_active_axes(event):
                self._end_pan()
        elif self._active_tool == "zoom" and self._zoom_rect_start is not None:
            if self._active_axes == self._determine_active_axes(event):
                self._end_zoom(event)

    # # Pan implementation (now works on self._active_axes)
    # def _start_pan(self, event):
    #     """Start panning operation on the active axes"""
    #     self._pan_start = (event.data_x, event.data_y)
    #     self._pan_start_limits = (
    #         self._active_axes.get_xlim(),
    #         self._active_axes.get_ylim(),
    #     )
    #     # self.status_label.value = "Panning axes..."

    # # def _do_pan(self, event):
    # #     """Perform panning on the active axes"""
    # #     if (
    # #         self._pan_start is None
    # #         or self._pan_start_limits is None
    # #         or self._active_axes is None
    # #     ):
    # #         return

    # #     # Calculate delta in data coordinates
    # #     dx = event.data_x - self._pan_start[0]
    # #     dy = event.data_y - self._pan_start[1]

    # #     # Apply pan (move in opposite direction)
    # #     start_xlim, start_ylim = self._pan_start_limits
    # #     new_xlim = (start_xlim[0] - dx, start_xlim[1] - dx)
    # #     new_ylim = (start_ylim[0] - dy, start_ylim[1] - dy)

    # #     self._active_axes.set_xlim(*new_xlim)
    # #     self._active_axes.set_ylim(*new_ylim)
    # def _do_pan(self, event):
    #     """Perform panning with single batched update"""
    #     if (
    #         self._pan_start is None
    #         or self._pan_start_limits is None
    #         or self._active_axes is None
    #     ):
    #         return

    #     # Calculate delta in data coordinates
    #     dx = event.data_x - self._pan_start[0]
    #     dy = event.data_y - self._pan_start[1]

    #     # Apply pan (move in opposite direction)
    #     start_xlim, start_ylim = self._pan_start_limits
    #     new_xlim = (start_xlim[0] - dx, start_xlim[1] - dx)
    #     new_ylim = (start_ylim[0] - dy, start_ylim[1] - dy)

    #     # ✅ Update both limits then draw once
    #     self._active_axes.set_xlim(*new_xlim)
    #     self._active_axes.set_ylim(*new_ylim)
    #     self.figure.draw()  # Single draw with hold_canvas

    # # In toolbar _start_pan:
    # def _start_pan(self, ax, x, y):
    #     """Start panning operation on the active axes"""
    #     # self._pan_start_canvas = (
    #     #     event.canvas_x,
    #     #     event.canvas_y,
    #     # )  # ✅ Store canvas coords

    #     inv = ax.transData.inverted()
    #     data_x, data_y = inv.transform((x, y))
    #     self._pan_start_point = (data_x, data_y)

    #     self._pan_start_limits = (ax.get_xlim(), ax.get_ylim())

    # # Store the coordinate transform parameters at pan start
    # self._pan_axes_bounds = {
    #     "x": self._active_axes.x,
    #     "y": self._active_axes.y,
    #     "width": self._active_axes.width,
    #     "height": self._active_axes.height,
    #     "xlim": self._pan_start_limits[0],
    #     "ylim": self._pan_start_limits[1],
    # }

    # # print(self._pan_axes_bounds)  # Debug

    # # self.status_label.value = "Panning axes..."

    # def _do_pan(self, event):
    #     """Perform panning using canvas coordinate deltas"""
    #     # print(self._pan_start_canvas, self._pan_start_limits, self._active_axes)
    #     if (
    #         self._pan_start_canvas is None
    #         or self._pan_start_limits is None
    #         or self._active_axes is None
    #     ):
    #         return

    #     # Calculate delta in CANVAS coordinates (stable reference)
    #     dx_canvas = event.canvas_x - self._pan_start_canvas[0]
    #     dy_canvas = event.canvas_y - self._pan_start_canvas[1]

    #     # Convert canvas deltas to data deltas using ORIGINAL transform parameters
    #     bounds = self._pan_axes_bounds
    #     dx_data = (dx_canvas / bounds["width"]) * (
    #         bounds["xlim"][1] - bounds["xlim"][0]
    #     )
    #     dy_data = -(dy_canvas / bounds["height"]) * (
    #         bounds["ylim"][1] - bounds["ylim"][0]
    #     )  # Note: negative for Y

    #     # Apply pan using original limits as reference
    #     start_xlim, start_ylim = self._pan_start_limits
    #     new_xlim = (start_xlim[0] - dx_data, start_xlim[1] - dx_data)
    #     new_ylim = (start_ylim[0] - dy_data, start_ylim[1] - dy_data)

    #     # Update limits and redraw
    #     self._active_axes.set_xlim(*new_xlim)
    #     self._active_axes.set_ylim(*new_ylim)
    #     self.figure.draw()

    # def _end_pan(self):
    #     """End panning operation"""
    #     self._pan_start = None
    #     self._pan_start_limits = None
    #     self._active_axes = None
    # self.status_label.value = "Pan complete"

    # Zoom implementation (now works on self._active_axes)
    # def _start_zoom(self, event):
    #     """Start zoom selection on the active axes"""
    #     self._zoom_rect_start = (event.data_x, event.data_y)
    #     self._zoom_rect_visible = True
    #     # self.status_label.value = "Selecting zoom region..."

    # def _update_zoom_preview(self, event):
    #     """Update zoom rectangle preview"""
    #     if self._zoom_rect_start is not None and self._active_axes is not None:
    #         x0, y0 = self._zoom_rect_start
    #         x1, y1 = event.data_x, event.data_y
    #         width = abs(x1 - x0)
    #         height = abs(y1 - y0)
    #         # self.status_label.value = f"Zoom region: {width:.2f} × {height:.2f}"

    # def _end_zoom(self, event):
    #     """Complete zoom operation on the active axes"""
    #     if self._zoom_rect_start is None or self._active_axes is None:
    #         return

    #     x0, y0 = self._zoom_rect_start
    #     x1, y1 = event.data_x, event.data_y

    #     # Ensure we have a proper rectangle (not just a click)
    #     min_size = 0.01  # Minimum zoom region size
    #     if abs(x1 - x0) < min_size or abs(y1 - y0) < min_size:
    #         # self.status_label.value = "Zoom region too small"
    #         self._zoom_rect_start = None
    #         self._active_axes = None
    #         return

    #     # Set new limits on the active axes
    #     new_xlim = (min(x0, x1), max(x0, x1))
    #     new_ylim = (min(y0, y1), max(y0, y1))

    #     self._active_axes.set_xlim(*new_xlim)
    #     self._active_axes.set_ylim(*new_ylim)

    #     self._zoom_rect_start = None
    #     self._active_axes = None
    #     # self.status_label.value = "Zoomed"

    def _draw_zoom_rectangle(self, start_canvas, end_canvas):
        """Draw zoom rectangle on the canvas"""
        if not self._zoom_rect_visible:
            return

        x1, y1 = start_canvas
        x2, y2 = end_canvas

        # Calculate rectangle coordinates
        rect_x = min(x1, x2)
        rect_y = min(y1, y2)
        rect_width = abs(x2 - x1)
        rect_height = abs(y2 - y1)

        # Draw rectangle with dashed border
        canvas = self.figure.canvas
        canvas.save()

        # Set rectangle style
        canvas.stroke_style = "red"
        canvas.line_width = 1
        canvas.set_line_dash([5, 5])  # Dashed line
        canvas.global_alpha = 0.8

        # Draw rectangle border
        canvas.stroke_rect(rect_x, rect_y, rect_width, rect_height)

        # Optional: fill with semi-transparent color
        canvas.fill_style = "rgba(255, 0, 0, 0.1)"  # Light red
        canvas.fill_rect(rect_x, rect_y, rect_width, rect_height)

        canvas.restore()

    def _clear_zoom_rectangle(self):
        """Clear the zoom rectangle by redrawing the figure"""
        if self._zoom_rect_visible:
            self._zoom_rect_visible = False
            # Redraw the entire figure to clear the rectangle
            self.figure.draw()

    def _start_zoom(self, event):
        """Start zoom selection on the active axes"""
        self._zoom_rect_start = (event.data_x, event.data_y)
        # Store canvas coordinates for rectangle drawing
        self._zoom_rect_start_canvas = (event.canvas_x, event.canvas_y)
        self._zoom_rect_visible = True
        # self.status_label.value = "Selecting zoom region..."

    # def _update_zoom_preview(self, event):
    #     """Update zoom rectangle preview"""
    #     if self._zoom_rect_start is not None and self._active_axes is not None:
    #         # Clear previous rectangle by redrawing
    #         self.figure.draw()

    #         # Draw new rectangle
    #         self._draw_zoom_rectangle(
    #             self._zoom_rect_start_canvas, (event.canvas_x, event.canvas_y)
    #         )

    #         # Update status
    #         x0, y0 = self._zoom_rect_start
    #         x1, y1 = event.data_x, event.data_y
    #         width = abs(x1 - x0)
    #         height = abs(y1 - y0)
    #         # self.status_label.value = f"Zoom region: {width:.2f} × {height:.2f}"

    def _update_zoom_preview(self, event):
        """Optimized zoom rectangle with minimal redraw"""
        if self._zoom_rect_start is not None and self._active_axes is not None:
            # Use the same pattern as pure ipycanvas example
            with hold_canvas(self.figure.canvas):
                # Redraw figure content (same as figure.draw() internals)
                self.figure.canvas.clear()
                self.figure.canvas.fill_style = self.figure.facecolor
                self.figure.canvas.fill_rect(
                    0, 0, self.figure.width, self.figure.height
                )

                for ax in self.figure.axes:
                    ax.draw()

                # Add zoom rectangle
                self._draw_zoom_rectangle(
                    self._zoom_rect_start_canvas, (event.canvas_x, event.canvas_y)
                )

    def _end_zoom(self, event):
        """Complete zoom operation on the active axes"""
        if self._zoom_rect_start is None or self._active_axes is None:
            return

        # Clear the rectangle first
        self._clear_zoom_rectangle()

        x0, y0 = self._zoom_rect_start
        x1, y1 = event.data_x, event.data_y

        # Ensure we have a proper rectangle (not just a click)
        min_size = 0.01  # Minimum zoom region size
        if abs(x1 - x0) < min_size or abs(y1 - y0) < min_size:
            # self.status_label.value = "Zoom region too small"
            self._zoom_rect_start = None
            self._zoom_rect_start_canvas = None
            self._active_axes = None
            return

        # Set new limits on the active axes
        new_xlim = (min(x0, x1), max(x0, x1))
        new_ylim = (min(y0, y1), max(y0, y1))

        self._active_axes.set_xlim(*new_xlim)
        self._active_axes.set_ylim(*new_ylim)

        # Clean up
        self._zoom_rect_start = None
        self._zoom_rect_start_canvas = None
        self._active_axes = None
        # self.status_label.value = "Zoomed"
        self.figure.draw()  # Final draw to ensure clean state

    # # Also update the tool deactivation to clear any active rectangle
    # def _on_zoom_clicked(self, button):
    #     """Activate/deactivate zoom tool"""
    #     if self._active_tool == "zoom":
    #         self._active_tool = None
    #         self._clear_zoom_rectangle()  # Clear any active rectangle
    #         self.status_label.value = "Zoom tool deactivated"
    #     else:
    #         self._active_tool = "zoom"
    #         self.status_label.value = (
    #             "Zoom tool active - drag on any plot to select region"
    #         )
    #     self._update_button_states()
