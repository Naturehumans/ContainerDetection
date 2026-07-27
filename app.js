// Initialize Proj4js with UTM Zone 48S
// Jakarta is roughly in 48S (EPSG:32748)
proj4.defs("EPSG:32748", "+proj=utm +zone=48 +south +datum=WGS84 +units=m +no_defs");
proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");

// Reference Point given by user
const REF_LON = 106.88178028;
const REF_LAT = -6.11260706;

// Container Dimensions
const CONTAINER_LENGTH = 6.0; // meters (X axis in grid)
const CONTAINER_WIDTH = 2.5; // meters (Y axis in grid)

// DOM Elements
const lonInput = document.getElementById('lon');
const latInput = document.getElementById('lat');
const rotInput = document.getElementById('rotation');
const calculateBtn = document.getElementById('calculateBtn');
const resultsArea = document.getElementById('resultsArea');
const gridCanvas = document.getElementById('gridCanvas');
const canvasTooltip = document.getElementById('canvasTooltip');
const ctx = gridCanvas.getContext('2d');

// Output Elements
const outUtmX = document.getElementById('outUtmX');
const outUtmY = document.getElementById('outUtmY');
const outRotX = document.getElementById('outRotX');
const outRotY = document.getElementById('outRotY');
const outSlot = document.getElementById('outSlot');

// Building geometry in Lon/Lat as provided by the user
const buildingPoints = {
    A: [106.88185392, -6.11239707],  // Point 5
    B: [106.88189726, -6.11245381],  // Point 4
    C: [106.88187588, -6.11246944],  // Point 3
    D: [106.88190898, -6.11251261],  // Point 2
    E: [106.88178028, -6.11260706],  // Point 1
    F: [106.88170742, -6.11250445]   // Point 6 (Reference point)
};

// Helper to convert index to letters (0 -> A, 1 -> B, ..., 26 -> AA)
function getColumnLetter(colIndex) {
    if (colIndex < 0) return "-" + getColumnLetter(-colIndex - 1);
    let temp, letter = '';
    while (colIndex >= 0) {
        temp = colIndex % 26;
        letter = String.fromCharCode(temp + 65) + letter;
        colIndex = Math.floor((colIndex - temp) / 26) - 1;
    }
    return letter;
}

calculateBtn.addEventListener('click', () => {
    const inputLon = parseFloat(lonInput.value);
    const inputLat = parseFloat(latInput.value);
    const rotationDeg = parseFloat(rotInput.value);

    if (isNaN(inputLon) || isNaN(inputLat) || isNaN(rotationDeg)) {
        alert("Please enter valid numbers for coordinates and rotation.");
        return;
    }

    // 1. Convert to UTM
    const refUTM = proj4("EPSG:4326", "EPSG:32748", buildingPoints.F);
    const inputUTM = proj4("EPSG:4326", "EPSG:32748", [inputLon, inputLat]);

    const utmX = inputUTM[0];
    const utmY = inputUTM[1];

    outUtmX.textContent = utmX.toFixed(2);
    outUtmY.textContent = utmY.toFixed(2);

    // Calculate rotated building polygon for visualization
    const angleRad = rotationDeg * (Math.PI / 180);
    const rotatedBuilding = {};
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    for (const [key, coords] of Object.entries(buildingPoints)) {
        const pUTM = proj4("EPSG:4326", "EPSG:32748", coords);
        const pdx = pUTM[0] - refUTM[0];
        const pdy = pUTM[1] - refUTM[1];

        // Coordinate system rotation
        const rx = pdx * Math.cos(angleRad) + pdy * Math.sin(angleRad);
        const ry = -pdx * Math.sin(angleRad) + pdy * Math.cos(angleRad);
        rotatedBuilding[key] = { x: rx, y: ry };

        if (rx < minX) minX = rx;
        if (rx > maxX) maxX = rx;
        if (ry < minY) minY = ry;
        if (ry > maxY) maxY = ry;
    }

    // 2. Calculate offsets from reference point for INPUT
    const dx = utmX - refUTM[0];
    const dy = utmY - refUTM[1];

    // 3. Apply Rotation to Input (Coordinate system rotation)
    const rotatedX = dx * Math.cos(angleRad) + dy * Math.sin(angleRad);
    const rotatedY = -dx * Math.sin(angleRad) + dy * Math.cos(angleRad);

    outRotX.textContent = rotatedX.toFixed(2) + " m";
    outRotY.textContent = rotatedY.toFixed(2) + " m";

    // 4. Calculate Container Grid Position
    let colIndex = Math.floor(rotatedX / CONTAINER_LENGTH);
    let rowIndex = Math.floor(rotatedY / CONTAINER_WIDTH);

    const colLetter = getColumnLetter(colIndex);
    const rowNumber = rowIndex >= 0 ? rowIndex + 1 : rowIndex;

    const slotName = `${colLetter}${rowNumber}`;
    outSlot.textContent = slotName;

    // Show Results
    resultsArea.classList.remove('hidden');
    resultsArea.style.display = 'grid';

    // 5. Draw Grid Visualization on Canvas
    drawCanvas(rotatedBuilding, rotatedX, rotatedY, minX, maxX, minY, maxY, colIndex, rowIndex);
});

// Ray-casting point in polygon algorithm
function pointInPolygon(point, vs) {
    let x = point.x, y = point.y;
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        let xi = vs[i].x, yi = vs[i].y;
        let xj = vs[j].x, yj = vs[j].y;
        let intersect = ((yi > y) != (yj > y))
            && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

// Check if a rectangle is inside the polygon with a small tolerance (to avoid dropping slots due to slightly skewed lines)
function isRectInPolygon(rx, ry, rw, rh, poly) {
    // Inset by 20% to allow small edge crossings but prevent completely hanging out
    const insetX = rw * 0.20; 
    const insetY = rh * 0.20;
    
    const corners = [
        { x: rx + insetX, y: ry + insetY },
        { x: rx + rw - insetX, y: ry + insetY },
        { x: rx + insetX, y: ry + rh - insetY },
        { x: rx + rw - insetX, y: ry + rh - insetY }
    ];
    
    // If any of the inset corners is outside the polygon, it means it crosses the line too much
    for (const corner of corners) {
        if (!pointInPolygon(corner, poly)) {
            return false;
        }
    }
    
    return true;
}

function drawCanvas(building, targetX, targetY, minX, maxX, minY, maxY, targetCol, targetRow) {
    // Add padding to bounding box for visual breathing room
    const padding = Math.max((maxX - minX) * 0.1, (maxY - minY) * 0.1, 5);
    const viewMinX = minX - padding;
    const viewMaxX = maxX + padding;
    const viewMinY = minY - padding;
    const viewMaxY = maxY + padding;

    const viewWidth = viewMaxX - viewMinX;
    const viewHeight = viewMaxY - viewMinY;

    // Set internal resolution
    gridCanvas.width = gridCanvas.clientWidth * 2;
    gridCanvas.height = gridCanvas.width * (viewHeight / viewWidth);
    gridCanvas.style.height = (gridCanvas.clientWidth * (viewHeight / viewWidth)) + "px";

    const scale = gridCanvas.width / viewWidth;

    // Helper to map meters to canvas pixels (Y axis inverted for screen coordinates)
    const mapX = (x) => (x - viewMinX) * scale;
    const mapY = (y) => (viewMaxY - y) * scale;

    ctx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);
    canvasData = [];

    // Polygon vertex array for hit testing
    const order = ['F', 'A', 'B', 'C', 'D', 'E'];
    const polyCoords = order.map(k => building[k]);

    // Draw Building Polygon
    ctx.beginPath();
    ctx.moveTo(mapX(polyCoords[0].x), mapY(polyCoords[0].y));
    for (let i = 1; i < polyCoords.length; i++) {
        ctx.lineTo(mapX(polyCoords[i].x), mapY(polyCoords[i].y));
    }
    ctx.closePath();

    // Fill building (yellow-ish as in user's image)
    ctx.fillStyle = "rgba(234, 179, 8, 0.3)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#eab308"; // Yellow border
    ctx.stroke();

    // Draw Grid within bounding box
    const startCol = Math.floor(minX / CONTAINER_LENGTH);
    const endCol = Math.ceil(maxX / CONTAINER_LENGTH);
    const startRow = Math.floor(minY / CONTAINER_WIDTH);
    const endRow = Math.ceil(maxY / CONTAINER_WIDTH);

    ctx.lineWidth = 1;

    let isTargetValid = false;

    for (let c = startCol; c <= endCol; c++) {
        for (let r = startRow; r <= endRow; r++) {
            const cx = c * CONTAINER_LENGTH;
            const cy = r * CONTAINER_WIDTH;

            // Check if this container cell is fully inside the polygon
            if (!isRectInPolygon(cx, cy, CONTAINER_LENGTH, CONTAINER_WIDTH, polyCoords)) {
                continue; // Skip if it exceeds bounds
            }

            const px = mapX(cx);
            const py = mapY(cy + CONTAINER_WIDTH); // Top-left of the cell on canvas
            const pWidth = CONTAINER_LENGTH * scale;
            const pHeight = CONTAINER_WIDTH * scale;

            const isTarget = (c === targetCol && r === targetRow);
            if (isTarget) isTargetValid = true;

            // Draw container slot
            ctx.beginPath();
            ctx.rect(px, py, pWidth, pHeight);

            if (isTarget) {
                ctx.fillStyle = "#10b981"; // Highlight target in green
                ctx.strokeStyle = "#047857";
            } else {
                ctx.fillStyle = "#f97316"; // Orange color for containers
                ctx.strokeStyle = "#c2410c";
            }

            ctx.fill();
            ctx.stroke();

            // Draw circle inside like user image (optional stylistic touch)
            ctx.beginPath();
            ctx.arc(px + pWidth / 2, py + pHeight / 2, Math.min(pWidth, pHeight) * 0.35, 0, Math.PI * 2);
            ctx.fillStyle = isTarget ? "#34d399" : "#fb923c";
            ctx.fill();

            // Save for hover
            const colLetter = getColumnLetter(c);
            const rowNumber = r >= 0 ? r + 1 : r;
            canvasData.push({
                x: px, y: py, w: pWidth, h: pHeight,
                label: `${colLetter}${rowNumber}`
            });
        }
    }

    // Update outSlot text if target is invalid
    if (!isTargetValid) {
        outSlot.innerHTML = `<span style="color: #ef4444; font-size: 1.5rem;">Out of Bounds</span>`;
    }

    // Draw Target Point (exact coordinates) as a small dot
    ctx.beginPath();
    ctx.arc(mapX(targetX), mapY(targetY), 5, 0, 2 * Math.PI);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#000000";
    ctx.stroke();
}

// Tooltip logic
gridCanvas.addEventListener('mousemove', (e) => {
    const rect = gridCanvas.getBoundingClientRect();
    const scaleX = gridCanvas.width / rect.width;
    const scaleY = gridCanvas.height / rect.height;

    const mouseX = (e.clientX - rect.left) * scaleX;
    const mouseY = (e.clientY - rect.top) * scaleY;

    let hovered = null;
    for (const cell of canvasData) {
        if (mouseX >= cell.x && mouseX <= cell.x + cell.w &&
            mouseY >= cell.y && mouseY <= cell.y + cell.h) {
            hovered = cell;
            break;
        }
    }

    if (hovered) {
        canvasTooltip.textContent = `Slot: ${hovered.label}`;
        canvasTooltip.style.left = (e.clientX + 15) + 'px';
        canvasTooltip.style.top = (e.clientY + 15) + 'px';
        canvasTooltip.classList.remove('hidden');
    } else {
        canvasTooltip.classList.add('hidden');
    }
});

gridCanvas.addEventListener('mouseleave', () => {
    canvasTooltip.classList.add('hidden');
});

// Add a new simulation button to the page
const simulateBtnHTML = `<button id="simulateBtn" type="button" style="margin-top: 1rem; background-color: var(--success-color);">Run 30-Reading Simulation</button>`;
document.getElementById('calculateBtn').insertAdjacentHTML('afterend', simulateBtnHTML);

// When clicked, ask Python for 30 averaged coordinates
document.getElementById('simulateBtn').addEventListener('click', async () => {
    try {
        const response = await fetch('/simulate');
        const data = await response.json();

        // Put the averaged data directly into your input fields
        document.getElementById('lon').value = data.avg_lon;
        document.getElementById('lat').value = data.avg_lat;

        // Automatically click the calculate button to see the grid result
        document.getElementById('calculateBtn').click();
    } catch (error) {
        alert("Simulation failed. Make sure your Python server (server.py) is running!");
    }
});
