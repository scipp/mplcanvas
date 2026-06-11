/**
 * Anywidget renderer for mplcanvas
 * Renders matplotlib figures using native browser canvas
 */

function render({ model, el }) {
  // Create container for canvas layers
  const container = document.createElement("div");
  container.style.position = "relative";
  container.style.display = "inline-block";

  const width = model.get("width");
  const height = model.get("height");
  const ncanvases = model.get("ncanvases");

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

  el.appendChild(container);

  // Handle draw commands from Python
  model.on("change:draw_commands", () => {
    const commands = model.get("draw_commands");
    drawFromCommands(canvases, commands, height);
  });

  // Initial draw if commands already exist
  const initialCommands = model.get("draw_commands");
  if (initialCommands && initialCommands.length > 0) {
    drawFromCommands(canvases, initialCommands, height);
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
      ctx.fillRect(x - collection.size / 2, y - collection.size / 2, collection.size, collection.size);
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