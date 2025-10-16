from matplotlib.colors import to_hex
import numpy as np


from .utils import flip_y


def draw_line(line, ax, canvas):
    # Get data coordinates
    xdata = line.get_xdata()
    ydata = line.get_ydata()

    if len(xdata) == 0 or len(ydata) == 0:
        return

    x, y = ax.transData.transform(np.array((xdata, ydata)).T).T
    y = flip_y(y, canvas)

    canvas.stroke_style = to_hex(line.get_color())
    canvas.line_width = line.get_linewidth()
    # Use numpy array for efficient drawing
    points = np.column_stack([x, y])
    canvas.stroke_lines(points)


def draw_ticks_and_labels(ax, canvas):
    # Draw ticks and labels on all sides
    tick_length = 6
    label_offset = 3
    font_size = 12
    canvas.font = f"{font_size}px sans-serif"
    canvas.fill_style = "black"
    canvas.text_align = "center"
    canvas.text_baseline = "top"

    # X axis ticks and labels (bottom)
    (xmin, xmax), (ymin, ymax) = ax.get_xlim(), ax.get_ylim()
    xticks = ax.get_xticks()
    xlabels = [lab.get_text() for lab in ax.get_xticklabels()]
    for tick, label in zip(xticks, xlabels, strict=True):
        if tick < xmin or tick > xmax:
            continue
        x, y = ax.transData.transform((tick, ymin))
        y = flip_y(y, canvas)
        # Tick
        canvas.begin_path()
        canvas.move_to(x, y)
        canvas.line_to(x, y - tick_length)
        canvas.stroke()
        # Label
        canvas.fill_text(label, x, y + tick_length + label_offset)

    # Y axis ticks and labels (left)
    canvas.text_align = "right"
    canvas.text_baseline = "middle"
    yticks = ax.get_yticks()
    ylabels = [lab.get_text() for lab in ax.get_yticklabels()]
    # xmin = ax.get_xlim()[0]
    for tick, label in zip(yticks, ylabels, strict=True):
        if tick < ymin or tick > ymax:
            continue
        x, y = ax.transData.transform((xmin, tick))
        y = flip_y(y, canvas)
        # Tick
        canvas.begin_path()
        canvas.move_to(x, y)
        canvas.line_to(x - tick_length, y)
        canvas.stroke()
        # Label
        canvas.fill_text(label, x - tick_length - label_offset, y)


def draw_axes(ax, canvas):
    # Draw frame

    # Apparently need to ask the axis limits for them to be set correctly
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    (xmin_disp, ymin_disp), (xmax_disp, ymax_disp) = ax.transData.transform(
        ((xmin, ymin), (xmax, ymax))
    )
    width = xmax_disp - xmin_disp
    height = ymax_disp - ymin_disp

    # (xmin_disp, ymin_disp), (xmax_disp, ymax_disp) = ax.transData.transform(
    #     ((xmin, ymin), (xmax, ymax))
    # )
    # width = xmax_disp - xmin_disp
    # height = ymax_disp - ymin_disp
    # print(f"Drawing axes at {xmin_disp},{ymin_disp} size {width}x{height}")

    # Set clipping region to axes area
    canvas.save()
    canvas.begin_path()
    canvas.rect(xmin_disp, ymin_disp, width, height)
    canvas.clip()

    # Draw all line artists
    for line in ax.lines:
        draw_line(line, ax, canvas)

    # # Draw frame
    # xmin, xmax = ax.get_xlim()
    # ymin, ymax = ax.get_ylim()
    (xmin_disp, ymin_disp), (xmax_disp, ymax_disp) = ax.transData.transform(
        ((xmin, ymin), (xmax, ymax))
    )
    width = xmax_disp - xmin_disp
    height = ymax_disp - ymin_disp
    # print(f"Drawing axes at {xmin_disp},{ymin_disp} size {width}x{height}")

    canvas.stroke_style = "black"
    canvas.line_width = 1.0
    canvas.stroke_rect(xmin_disp, ymin_disp, width, height)

    # Restore canvas state (remove clipping)
    canvas.restore()

    # Draw ticks and labels
    draw_ticks_and_labels(ax, canvas)
