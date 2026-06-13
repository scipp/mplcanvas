/**
 * Anywidget renderer for mplcanvas
 * Renders matplotlib figures using native browser canvas with interactive tools
 */

function render({ model, el }) {
  const width = model.get("width");
  const height = model.get("height");
  const ncanvases = model.get("ncanvases");

  // Load Font Awesome if not already loaded
  if (!document.querySelector('link[href*="font-awesome"]')) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css";
    document.head.appendChild(link);
  }

  // Create main container with toolbar on the left
  const mainContainer = document.createElement("div");
  mainContainer.className = "mplcanvas-main-container";

  // Create toolbar
  const toolbar = createToolbar(model);
  mainContainer.appendChild(toolbar);

  // Create container for canvas layers
  const container = document.createElement("div");
  container.className = "mplcanvas-container";
  container.style.width = `${width}px`;
  container.style.height = `${height}px`;
  container.style.position = "relative";
  container.style.display = "inline-block";
  container.style.cursor = "default";

  // Create canvas layers (one per axes + one for overlays)
  const canvases = [];
  for (let i = 0; i < ncanvases; i++) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.style.position = "absolute";
    canvas.style.left = "0";
    canvas.style.top = "0";

    container.appendChild(canvas);
    canvases.push(canvas);
  }

  mainContainer.appendChild(container);
  el.appendChild(mainContainer);

  // The last canvas is the overlay for drawing zoom rectangles, etc.
  const overlayCanvas = canvases[ncanvases - 1];

  // State for interactions
  const state = {
    activeTool: "",
    activeAxes: null,
    isDrawing: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    panStartLimits: null,
    panDx: 0,
    panDy: 0,
    originalCommands: null,
  };

  // Handle draw commands from Python
  model.on("change:draw_commands", () => {
    const commands = model.get("draw_commands");
    drawFromCommands(canvases, commands, height);
    // Store original commands for pan operations
    state.originalCommands = JSON.parse(JSON.stringify(commands));
  });

  // Handle tool changes
  model.on("change:active_tool", () => {
    const tool = model.get("active_tool");
    state.activeTool = tool;
    updateCursor(container, tool);
  });

  // Initial draw if commands already exist
  const initialCommands = model.get("draw_commands");
  if (initialCommands && initialCommands.length > 0) {
    drawFromCommands(canvases, initialCommands, height);
    state.originalCommands = JSON.parse(JSON.stringify(initialCommands));
  }

  // Setup mouse interactions
  setupInteractions(container, overlayCanvas, canvases, state, model, height);
}

function createToolbar(model) {
  const toolbar = document.createElement("div");
  toolbar.className = "mplcanvas-toolbar";

  // Home button
  const homeBtn = createToolButton("fa-solid fa-house", "Reset to home view", () => {
    // Trigger home action in Python by incrementing the trigger
    const currentTrigger = model.get("trigger_home");
    model.set("trigger_home", currentTrigger + 1);
    model.save_changes();
  });
  toolbar.appendChild(homeBtn);

  // Pan button
  const panBtn = createToolButton("fa-solid fa-arrows-up-down-left-right", "Pan axes with left mouse, zoom with right", () => {
    const currentTool = model.get("active_tool");
    if (currentTool === "pan") {
      model.set("active_tool", "");
      panBtn.classList.remove("active");
    } else {
      model.set("active_tool", "pan");
      panBtn.classList.add("active");
    }
    model.save_changes();
  }, true);
  toolbar.appendChild(panBtn);

  // Zoom button
  const zoomBtn = createToolButton("fa-regular fa-square", "Zoom to rectangle", () => {
    const currentTool = model.get("active_tool");
    if (currentTool === "zoom") {
      model.set("active_tool", "");
      zoomBtn.classList.remove("active");
    } else {
      model.set("active_tool", "zoom");
      zoomBtn.classList.add("active");
    }
    model.save_changes();
  }, true);
  toolbar.appendChild(zoomBtn);

  // Listen for tool changes to update button states
  model.on("change:active_tool", () => {
    const tool = model.get("active_tool");
    panBtn.classList.toggle("active", tool === "pan");
    zoomBtn.classList.toggle("active", tool === "zoom");
  });

  return toolbar;
}

function createToolButton(iconClass, tooltip, onClick, isToggle = false) {
  const btn = document.createElement("button");
  btn.className = "mplcanvas-tool-button";
  const icon = document.createElement("i");
  icon.className = iconClass;
  btn.appendChild(icon);
  btn.title = tooltip;
  btn.onclick = onClick;
  return btn;
}

function updateCursor(container, tool) {
  if (tool === "zoom") {
    container.style.cursor = "crosshair";
  } else if (tool === "pan") {
    container.style.cursor = "move";
  } else {
    container.style.cursor = "default";
  }
}

function setupInteractions(container, overlayCanvas, canvases, state, model, canvasHeight) {
  container.addEventListener("mousedown", (e) => {
    if (!state.activeTool) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Find which axes was clicked
    const commands = model.get("draw_commands");
    state.activeAxes = findAxesAtPosition(x, y, commands, canvasHeight);

    if (!state.activeAxes) return;

    state.isDrawing = true;
    state.startX = x;
    state.startY = y;
    state.currentX = x;
    state.currentY = y;

    if (state.activeTool === "pan") {
      state.panStartLimits = {
        xlim: [...state.activeAxes.limits.xlim],
        ylim: [...state.activeAxes.limits.ylim],
      };
      state.panDx = 0;
      state.panDy = 0;
      container.style.cursor = "grabbing";
    }
  });

  container.addEventListener("mousemove", (e) => {
    if (!state.isDrawing || !state.activeAxes) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    state.currentX = x;
    state.currentY = y;

    if (state.activeTool === "zoom") {
      drawZoomRectangle(overlayCanvas, state, state.activeAxes.limits, canvasHeight);
    } else if (state.activeTool === "pan") {
      // Calculate pan delta
      state.panDx = state.currentX - state.startX;
      state.panDy = state.currentY - state.startY;

      // Redraw with pan offset
      redrawWithPanOffset(canvases, state, canvasHeight);
    }
  });

  container.addEventListener("mouseup", (e) => {
    if (!state.isDrawing || !state.activeAxes) return;

    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (state.activeTool === "zoom") {
      completeZoom(state, model, canvasHeight);
    } else if (state.activeTool === "pan") {
      // Store the canvas index before resetting state
      const canvasIndex = state.activeAxes.canvas_index;

      // Finalize pan by updating matplotlib axes
      completePan(state, model, canvasHeight);

      // Immediately redraw without offset to remove visual lag
      if (state.originalCommands && state.originalCommands[canvasIndex]) {
        const canvas = canvases[canvasIndex];
        const ctx = canvas.getContext("2d");
        const commands = state.originalCommands[canvasIndex];

        // Clear and redraw at original position
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Set up clipping region
        ctx.save();
        ctx.beginPath();
        const limits = commands.limits;
        ctx.rect(limits.xmin_disp, limits.ymin_disp, limits.width, limits.height);
        ctx.clip();

        // Draw all lines
        for (const line of commands.lines) {
          drawLine(ctx, line, canvasHeight);
        }

        // Draw all collections
        for (const collection of commands.collections) {
          drawCollection(ctx, collection, canvasHeight);
        }

        ctx.restore();

        // Draw frame and ticks
        drawFrame(ctx, commands.frame, canvasHeight);
        drawTicksAndLabels(ctx, commands.ticks, canvasHeight);
      }

      container.style.cursor = "move";
    }

    state.isDrawing = false;
    state.activeAxes = null;
    state.panStartLimits = null;
    state.panDx = 0;
    state.panDy = 0;

    // Clear overlay
    const ctx = overlayCanvas.getContext("2d");
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  });

  container.addEventListener("mouseleave", () => {
    if (state.isDrawing) {
      // If panning, finalize
      if (state.activeTool === "pan" && state.activeAxes) {
        const canvasIndex = state.activeAxes.canvas_index;
        completePan(state, model, canvasHeight);

        // Immediately redraw without offset
        if (state.originalCommands && state.originalCommands[canvasIndex]) {
          const canvas = canvases[canvasIndex];
          const ctx = canvas.getContext("2d");
          const commands = state.originalCommands[canvasIndex];

          ctx.clearRect(0, 0, canvas.width, canvas.height);

          ctx.save();
          ctx.beginPath();
          const limits = commands.limits;
          ctx.rect(limits.xmin_disp, limits.ymin_disp, limits.width, limits.height);
          ctx.clip();

          for (const line of commands.lines) {
            drawLine(ctx, line, canvasHeight);
          }

          for (const collection of commands.collections) {
            drawCollection(ctx, collection, canvasHeight);
          }

          ctx.restore();

          drawFrame(ctx, commands.frame, canvasHeight);
          drawTicksAndLabels(ctx, commands.ticks, canvasHeight);
        }
      }

      state.isDrawing = false;
      state.activeAxes = null;
      state.panStartLimits = null;
      state.panDx = 0;
      state.panDy = 0;

      // Clear overlay
      const ctx = overlayCanvas.getContext("2d");
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

      if (state.activeTool === "pan") {
        container.style.cursor = "move";
      }
    }
  });
}

function findAxesAtPosition(x, y, commandsList, canvasHeight) {
  const yFlipped = flipY(y, canvasHeight);

  for (const commands of commandsList) {
    const limits = commands.limits;
    if (
      x >= limits.xmin_disp &&
      x <= limits.xmax_disp &&
      yFlipped >= limits.ymin_disp &&
      yFlipped <= limits.ymax_disp
    ) {
      return {
        canvas_index: commands.canvas_index,
        limits: {
          xmin: limits.xmin,
          xmax: limits.xmax,
          ymin: limits.ymin,
          ymax: limits.ymax,
          xmin_disp: limits.xmin_disp,
          xmax_disp: limits.xmax_disp,
          ymin_disp: limits.ymin_disp,
          ymax_disp: limits.ymax_disp,
          width: limits.width,
          height: limits.height,
        },
      };
    }
  }
  return null;
}

function drawZoomRectangle(canvas, state, limits, canvasHeight) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Mouse coordinates are in HTML canvas space (y=0 at top)
  // We need to clamp them to the axes bounds, but the bounds are in matplotlib space (y=0 at bottom)
  // So we need to convert the bounds to HTML canvas space for clamping
  const limitsYMinHTML = flipY(limits.ymax_disp, canvasHeight);
  const limitsYMaxHTML = flipY(limits.ymin_disp, canvasHeight);

  // Clamp coordinates to axes bounds in HTML canvas space
  const x1 = Math.max(limits.xmin_disp, Math.min(limits.xmax_disp, state.startX));
  const x2 = Math.max(limits.xmin_disp, Math.min(limits.xmax_disp, state.currentX));
  const y1 = Math.max(limitsYMinHTML, Math.min(limitsYMaxHTML, state.startY));
  const y2 = Math.max(limitsYMinHTML, Math.min(limitsYMaxHTML, state.currentY));

  // Calculate rectangle
  const rectX = Math.min(x1, x2);
  const rectY = Math.min(y1, y2);
  const rectWidth = Math.abs(x2 - x1);
  const rectHeight = Math.abs(y2 - y1);

  // Draw rectangle in HTML canvas coordinates
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;
  ctx.setLineDash([5, 5]);
  ctx.strokeRect(rectX, rectY, rectWidth, rectHeight);
  ctx.setLineDash([]);
}

function completeZoom(state, model, canvasHeight) {
  const limits = state.activeAxes.limits;

  // Minimum zoom region size
  const minSize = 5;
  const dx = Math.abs(state.currentX - state.startX);
  const dy = Math.abs(state.currentY - state.startY);

  if (dx < minSize || dy < minSize) {
    return; // Too small, ignore
  }

  // Convert HTML canvas coordinates (where mouse events happen) to matplotlib space
  const startYFlipped = flipY(state.startY, canvasHeight);
  const currentYFlipped = flipY(state.currentY, canvasHeight);

  // Convert canvas coordinates to data coordinates
  const xRange = limits.xmax - limits.xmin;
  const yRange = limits.ymax - limits.ymin;
  const xScale = xRange / limits.width;
  const yScale = yRange / limits.height;

  const x1Canvas = Math.min(state.startX, state.currentX);
  const x2Canvas = Math.max(state.startX, state.currentX);
  const y1Canvas = Math.min(startYFlipped, currentYFlipped);
  const y2Canvas = Math.max(startYFlipped, currentYFlipped);

  const x1Data = limits.xmin + (x1Canvas - limits.xmin_disp) * xScale;
  const x2Data = limits.xmin + (x2Canvas - limits.xmin_disp) * xScale;
  const y1Data = limits.ymin + (y1Canvas - limits.ymin_disp) * yScale;
  const y2Data = limits.ymin + (y2Canvas - limits.ymin_disp) * yScale;

  // Update axis limits
  model.set("axis_limits_update", {
    canvas_index: state.activeAxes.canvas_index,
    xlim: [x1Data, x2Data],
    ylim: [y1Data, y2Data],
  });
  model.save_changes();
}

function completePan(state, model, canvasHeight) {
  const limits = state.activeAxes.limits;

  // Get the final pan delta
  const dx = state.panDx;
  const dy = state.panDy;

  // Convert to data coordinates
  const xRange = limits.xmax - limits.xmin;
  const yRange = limits.ymax - limits.ymin;
  const xScale = xRange / limits.width;
  const yScale = yRange / limits.height;

  // Note: dy is negated because HTML canvas y increases downward,
  // but matplotlib y increases upward
  const xDataDelta = -dx * xScale;
  const yDataDelta = dy * yScale;

  // Apply delta to original limits
  const newXMin = state.panStartLimits.xlim[0] + xDataDelta;
  const newXMax = state.panStartLimits.xlim[1] + xDataDelta;
  const newYMin = state.panStartLimits.ylim[0] + yDataDelta;
  const newYMax = state.panStartLimits.ylim[1] + yDataDelta;

  // Update axis limits
  model.set("axis_limits_update", {
    canvas_index: state.activeAxes.canvas_index,
    xlim: [newXMin, newXMax],
    ylim: [newYMin, newYMax],
  });
  model.save_changes();
}

function redrawWithPanOffset(canvases, state, canvasHeight) {
  if (!state.originalCommands) return;

  const canvasIndex = state.activeAxes.canvas_index;
  const canvas = canvases[canvasIndex];
  const ctx = canvas.getContext("2d");
  const commands = state.originalCommands[canvasIndex];

  if (!commands) return;

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const limits = commands.limits;
  const panDx = state.panDx;
  const panDy = state.panDy;

  // Set up clipping region for data (at axes spines)
  ctx.save();
  ctx.beginPath();
  ctx.rect(limits.xmin_disp, limits.ymin_disp, limits.width, limits.height);
  ctx.clip();

  // Draw lines with pan offset
  for (const line of commands.lines) {
    drawLineWithOffset(ctx, line, canvasHeight, panDx, panDy);
  }

  // Draw collections with pan offset
  for (const collection of commands.collections) {
    drawCollectionWithOffset(ctx, collection, canvasHeight, panDx, panDy);
  }

  // Restore context (remove clipping)
  ctx.restore();

  // Draw frame (no offset)
  drawFrame(ctx, commands.frame, canvasHeight);

  // Draw ticks and labels with partial offsets
  drawTicksAndLabelsWithOffset(ctx, commands.ticks, canvasHeight, panDx, panDy);
}

function drawLineWithOffset(ctx, line, canvasHeight, offsetX, offsetY) {
  if (line.points.length === 0) return;

  ctx.strokeStyle = line.stroke_style;
  ctx.lineWidth = line.line_width;

  ctx.beginPath();
  const firstPoint = line.points[0];
  ctx.moveTo(firstPoint[0] + offsetX, flipY(firstPoint[1], canvasHeight) + offsetY);

  for (let i = 1; i < line.points.length; i++) {
    const point = line.points[i];
    ctx.lineTo(point[0] + offsetX, flipY(point[1], canvasHeight) + offsetY);
  }

  ctx.stroke();
}

function drawCollectionWithOffset(ctx, collection, canvasHeight, offsetX, offsetY) {
  ctx.fillStyle = collection.fill_style;
  ctx.strokeStyle = collection.stroke_style;

  for (const point of collection.points) {
    const x = point[0] + offsetX;
    const y = flipY(point[1], canvasHeight) + offsetY;

    if (collection.marker_type === "square") {
      ctx.fillRect(
        x - collection.size / 2,
        y - collection.size / 2,
        collection.size,
        collection.size
      );
    } else {
      // circle
      ctx.beginPath();
      ctx.arc(x, y, collection.size, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
}

function drawTicksAndLabelsWithOffset(ctx, ticks, canvasHeight, offsetX, offsetY) {
  const tickLength = ticks.tick_length;
  const labelOffset = ticks.label_offset;
  const fontSize = 12;

  ctx.font = `${fontSize}px sans-serif`;
  ctx.fillStyle = "black";
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;

  // X-axis ticks and labels (only horizontal offset)
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (const tick of ticks.xticks) {
    const x = tick.x + offsetX;
    const y = flipY(tick.y, canvasHeight);

    // Draw tick
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x, y + tickLength);
    ctx.stroke();

    // Draw label
    ctx.fillText(tick.label, x, y + tickLength + labelOffset);
  }

  // Y-axis ticks and labels (only vertical offset)
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (const tick of ticks.yticks) {
    const x = tick.x;
    const y = flipY(tick.y, canvasHeight) + offsetY;

    // Draw tick
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - tickLength, y);
    ctx.stroke();

    // Draw label
    ctx.fillText(tick.label, x - tickLength - labelOffset, y);
  }

  // X-axis label (no offset)
  if (ticks.xlabel) {
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(ticks.xlabel.text, ticks.xlabel.x, ticks.xlabel.y);
  }

  // Y-axis label (no offset, rotated)
  if (ticks.ylabel) {
    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const y = flipY(ticks.ylabel.y, canvasHeight);
    ctx.translate(ticks.ylabel.x, y);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(ticks.ylabel.text, 0, 0);
    ctx.restore();
  }
}

function drawFromCommands(canvases, commandsList, canvasHeight) {
  // Each entry in commandsList is for one axes
  for (const commands of commandsList) {
    const canvasIndex = commands.canvas_index;
    const canvas = canvases[canvasIndex];
    const ctx = canvas.getContext("2d");

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Set up clipping region
    ctx.save();
    ctx.beginPath();
    const limits = commands.limits;
    ctx.rect(limits.xmin_disp, limits.ymin_disp, limits.width, limits.height);
    ctx.clip();

    // Draw all lines
    for (const line of commands.lines) {
      drawLine(ctx, line, canvasHeight);
    }

    // Draw all collections (scatter plots)
    for (const collection of commands.collections) {
      drawCollection(ctx, collection, canvasHeight);
    }

    // Restore context (remove clipping)
    ctx.restore();

    // Draw frame
    drawFrame(ctx, commands.frame, canvasHeight);

    // Draw ticks and labels
    drawTicksAndLabels(ctx, commands.ticks, canvasHeight);
  }
}

function drawLine(ctx, line, canvasHeight) {
  if (line.points.length === 0) return;

  ctx.strokeStyle = line.stroke_style;
  ctx.lineWidth = line.line_width;

  ctx.beginPath();
  const firstPoint = line.points[0];
  ctx.moveTo(firstPoint[0], flipY(firstPoint[1], canvasHeight));

  for (let i = 1; i < line.points.length; i++) {
    const point = line.points[i];
    ctx.lineTo(point[0], flipY(point[1], canvasHeight));
  }

  ctx.stroke();
}

function drawCollection(ctx, collection, canvasHeight) {
  ctx.fillStyle = collection.fill_style;
  ctx.strokeStyle = collection.stroke_style;

  for (const point of collection.points) {
    const x = point[0];
    const y = flipY(point[1], canvasHeight);

    if (collection.marker_type === "square") {
      ctx.fillRect(
        x - collection.size / 2,
        y - collection.size / 2,
        collection.size,
        collection.size
      );
    } else {
      // circle
      ctx.beginPath();
      ctx.arc(x, y, collection.size, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
}

function drawFrame(ctx, frame, canvasHeight) {
  ctx.strokeStyle = frame.stroke_style;
  ctx.lineWidth = frame.line_width;
  ctx.strokeRect(frame.x, frame.y, frame.width, frame.height);
}

function drawTicksAndLabels(ctx, ticks, canvasHeight) {
  const tickLength = ticks.tick_length;
  const labelOffset = ticks.label_offset;
  const fontSize = 12;

  ctx.font = `${fontSize}px sans-serif`;
  ctx.fillStyle = "black";
  ctx.strokeStyle = "black";
  ctx.lineWidth = 1;

  // X-axis ticks and labels
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (const tick of ticks.xticks) {
    const x = tick.x;
    const y = flipY(tick.y, canvasHeight);

    // Draw tick
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x, y + tickLength);
    ctx.stroke();

    // Draw label
    ctx.fillText(tick.label, x, y + tickLength + labelOffset);
  }

  // Y-axis ticks and labels
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (const tick of ticks.yticks) {
    const x = tick.x;
    const y = flipY(tick.y, canvasHeight);

    // Draw tick
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - tickLength, y);
    ctx.stroke();

    // Draw label
    ctx.fillText(tick.label, x - tickLength - labelOffset, y);
  }

  // X-axis label
  if (ticks.xlabel) {
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(ticks.xlabel.text, ticks.xlabel.x, ticks.xlabel.y);
  }

  // Y-axis label (rotated)
  if (ticks.ylabel) {
    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const y = flipY(ticks.ylabel.y, canvasHeight);
    ctx.translate(ticks.ylabel.x, y);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(ticks.ylabel.text, 0, 0);
    ctx.restore();
  }
}

function flipY(y, canvasHeight) {
  return canvasHeight - y;
}

export default { render };