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
        # self._zoom_rect_start = None
        # self._pan_info_canvas = None
        self._pan_info = None
        # self._pan_info_point = None
        # self._pan_info_limits = None
        self._zoom_info = None
        self._active_axes = None  # Which axes is currently being interacted with
        self._tools_lock = False

        # Store home views for all axes (will be populated as axes are added)
        self._home_views = {}  # {axes_id: (xlim, ylim)}

        # # Zoom rectangle state
        # self._zoom_rect_start = None
        # self._zoom_rect_current = None
        # self._zoom_rect_visible = False

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
            ax.autoscale()

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
            # self._clear_zoom_rectangle()  # Clear any active rectangle

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

    # def _store_home_view(self, axes):
    #     """Store the current view of an axes as its home view"""
    #     axes_id = id(axes)
    #     self._home_views[axes_id] = (axes.get_xlim(), axes.get_ylim())

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
            # self._do_pan(ax, data_x, data_y)
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
            # self._active_axes = self._determine_active_axes(event)
            # if self._active_axes:
            self._start_pan(x, y)
        elif self._active_tool == "zoom":
            # self._active_axes = self._determine_active_axes(event)
            self._start_zoom(x, canvas_y)

        # if not self._point_in_axes(x, y):
        #     return

    def _on_canvas_mouse_up(self, x: float, y: float):
        if self._active_tool == "pan" and self._pan_info is not None:
            self._end_pan()
        elif self._active_tool == "zoom":
            # print("Ending zoom", x, y)
            self._end_zoom(x, y)

    # In toolbar _start_pan:
    def _start_pan(self, x, y):
        """Start panning operation on the active axes"""

        ax = self._active_axes

        # inv = ax.transData.inverted()
        # data_x, data_y = inv.transform((x, y))
        # self._pan_info_point = (data_x, data_y)
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

        # self._pan_info_limits = (ax.get_xlim(), ax.get_ylim())
        # print("self._pan_info_point", self._pan_info_point)

    # def _do_pan(self, ax, data_x, data_y):
    def _do_pan(self, x, y):
        # """Perform panning using canvas coordinate deltas"""
        # print(self._pan_info_canvas, self._pan_info_limits, self._active_axes)
        if (
            self._pan_info is None
            # or self._pan_info_limits is None
            # or self._active_axes is None
        ):
            return

        ax = self._active_axes

        dx = (x - self._pan_info["origin"][0]) * self._pan_info["scale"][0]
        dy = (y - self._pan_info["origin"][1]) * self._pan_info["scale"][1]

        # Apply pan using original limits as reference
        start_xlim, start_ylim = self._pan_info["limits"]

        # print("start point", self._pan_info_point)
        # print("data point", (data_x, data_y))
        # print("delta", (dx, dy))
        # print("start limits", self._pan_info_limits)

        new_xlim = (start_xlim[0] - dx, start_xlim[1] - dx)
        new_ylim = (start_ylim[0] - dy, start_ylim[1] - dy)
        # print("new limits", new_xlim, new_ylim)

        # Update limits and redraw
        ax.set(xlim=new_xlim, ylim=new_ylim)
        # self.figure.mpl_figure.canvas.draw_idle()
        self.figure.draw(ax=ax)

    def _end_pan(self):
        """End panning operation"""
        self._pan_info = None
        self._active_axes = None
        # self._pan_info_limits = None
        # self._active_axes = None

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

        # print(x1, y1)
        # print(x2, y2)

        # Calculate rectangle coordinates
        rect_x = min(x1, x2)
        rect_y = min(y1, y2)
        rect_width = abs(x2 - x1)
        rect_height = abs(y2 - y1)
        self._zoom_info["rectangle"] = (rect_x, rect_y, rect_width, rect_height)

        with hold_canvas(canvas):
            # Redraw figure content (same as figure.draw() internals)
            canvas.clear()
            # canvas.fill_style = self.figure.facecolor
            # canvas.fill_rect(0, 0, self.figure.width, self.figure.height)

            # for ax in self.figure.axes:
            #     ax.draw()

            # # Draw rectangle with dashed border
            # canvas = self.figure.drawing_canvas
            # # canvas.save()

            # Set rectangle style
            canvas.stroke_style = "black"
            canvas.line_width = 1
            # canvas.set_line_dash([5, 5])  # Dashed line
            # canvas.global_alpha = 0.8

            # Draw rectangle border
            canvas.stroke_rect(*self._zoom_info["rectangle"])

            # # Optional: fill with semi-transparent color
            # canvas.fill_style = "rgba(255, 0, 0, 0.1)"  # Light red
            # canvas.fill_rect(rect_x, rect_y, rect_width, rect_height)

            # canvas.restore()

    def _end_zoom(self, x, y):
        """Complete zoom operation on the active axes"""
        # if self._zoom_rect_start is None or self._active_axes is None:
        #     return
        # self._zoom_info = None
        self.figure.drawing_canvas.clear()
        # self.figure.draw()

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
        # ax = self._active_axes
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

        # new_xlim = (min(x0, x1), max(x0, x1))
        # new_ylim = (min(y0, y1), max(y0, y1))

        self._active_axes.set_xlim(sorted([xdata_1, xdata_2]))
        self._active_axes.set_ylim(sorted([ydata_1, ydata_2]))

        # Clean up
        # self.status_label.value = "Zoomed"
        self.figure.draw(ax=self._active_axes)  # Final draw to ensure clean state
        self._zoom_info = None
        self._active_axes = None

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
