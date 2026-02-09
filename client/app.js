// DOM Elements
const cameraFeed = document.getElementById('camera-feed');
const canvas = document.getElementById('ocr-canvas');
const ctx = canvas.getContext('2d');
const manualInput = document.getElementById('manual-input');
const searchBtn = document.getElementById('search-btn');
const resultsContainer = document.getElementById('results-container');
const scannerStatus = document.getElementById('scanner-status');
const loadingSpinner = document.getElementById('loading-spinner');
const searchHint = document.getElementById('search-hint');

// Configuration
const API_URL = 'http://localhost:8000/api/search'; // Adjust if testing on device
const ROI_WIDTH = 300;
const ROI_HEIGHT = 100;
const SCAN_INTERVAL_MS = 800; // OCR frequency
const MODEL_REGEX = /([A-Z]{5}-[0-9]{2})/; // Strict model number pattern

// State
let isScanning = false;
let tesseractWorker = null;
let scanTimer = null;
let isProcessing = false;
let lastScannedCode = null;
let scanCooldown = false;

// Initialization
async function init() {
    updateStatus('Initializing System...');
    try {
        await initCamera();
        await initTesseract();
        startScanning();
    } catch (e) {
        updateStatus('Init Error: ' + e.message, true);
        console.error(e);
    }
}

// Camera Setup
async function initCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        });
        cameraFeed.srcObject = stream;

        // Wait for metadata to set canvas size
        cameraFeed.onloadedmetadata = () => {
            canvas.width = ROI_WIDTH;
            canvas.height = ROI_HEIGHT;
        };
    } catch (err) {
        throw new Error("Camera access denied");
    }
}

// Tesseract Setup
async function initTesseract() {
    updateStatus('Loading OCR Model...');
    tesseractWorker = await Tesseract.createWorker('eng');

    await tesseractWorker.setParameters({
        tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-',
    });

    updateStatus('Ready to Scan');
}

// Status Helper
function updateStatus(msg, isError = false) {
    scannerStatus.textContent = msg;
    scannerStatus.className = isError
        ? "absolute top-4 left-0 w-full text-center text-sm text-red-400 font-mono font-bold"
        : "absolute top-4 left-0 w-full text-center text-sm text-gray-300 font-mono";
}

// Scanning Logic
function startScanning() {
    if (isScanning) return;
    isScanning = true;
    scanTimer = setInterval(processFrame, SCAN_INTERVAL_MS);
}

function stopScanning() {
    isScanning = false;
    clearInterval(scanTimer);
}

async function processFrame() {
    if (!tesseractWorker || !cameraFeed.videoWidth || isProcessing || scanCooldown) return;

    // Draw ROI (Center Crop)
    const vidW = cameraFeed.videoWidth;
    const vidH = cameraFeed.videoHeight;
    const sx = (vidW - ROI_WIDTH) / 2;
    const sy = (vidH - ROI_HEIGHT) / 2;

    ctx.drawImage(cameraFeed, sx, sy, ROI_WIDTH, ROI_HEIGHT, 0, 0, ROI_WIDTH, ROI_HEIGHT);

    // OCR
    isProcessing = true;
    try {
        const imgData = canvas.toDataURL('image/png');
        const result = await tesseractWorker.recognize(imgData);
        const text = result.data.text.trim();

        // Check for Model Number
        const match = text.match(MODEL_REGEX);
        if (match) {
            const detectedCode = match[0];

            // Only process if different from last successful scan or cooldown expired
            if (detectedCode !== lastScannedCode) {
                console.log("Detected:", detectedCode);
                lastScannedCode = detectedCode;

                // UX Feedback
                updateStatus(`Detected: ${detectedCode}`);
                manualInput.value = detectedCode;

                // Trigger Search
                performSearch(detectedCode, true); // true = fromOCR
            }
        }
    } catch (err) {
        console.error("OCR Error", err);
    } finally {
        isProcessing = false;
    }
}

// Search Logic
async function performSearch(query, fromOCR = false) {
    if (!query) return;

    // UI Loading State
    loadingSpinner.classList.remove('hidden');
    searchHint.textContent = fromOCR ? "Searching detected code..." : "Searching...";

    // Cooldown logic for OCR
    if (fromOCR) {
        scanCooldown = true;
        // Stop scanning temporarily or just ignore new results?
        // Let's ignore new results until this completes
    }

    try {
        const res = await fetch(`${API_URL}?keyword=${encodeURIComponent(query)}`);
        const data = await res.json();

        loadingSpinner.classList.add('hidden');

        if (data.status === 'success' && data.data && data.data.length > 0) {
            renderResults(data.data);
            searchHint.textContent = `Found ${data.data.length} results in ${data.duration_sec}s`;
            searchHint.className = "text-xs text-green-400 mt-2 h-4 transition-all";

            // Clear last scanned code after a while so we can scan it again if needed
            setTimeout(() => { lastScannedCode = null; scanCooldown = false; }, 5000);

        } else {
            // FAILURE CASE handles
            handleSearchFailure(data, fromOCR);
        }

    } catch (err) {
        loadingSpinner.classList.add('hidden');
        searchHint.textContent = "Network Error. Please try again.";
        searchHint.className = "text-xs text-red-500 mt-2 h-4 transition-all";
        scanCooldown = false;
        lastScannedCode = null; // Allow retry
    }
}

function handleSearchFailure(data, fromOCR) {
    if (fromOCR) {
        // HYBRID FALLBACK LOGIC
        updateStatus("Scan Failed. Try Product Name.", true);
        searchHint.textContent = "Code not found. Switch to manual name search.";
        searchHint.className = "text-xs text-orange-400 mt-2 h-4 transition-all font-bold";

        // Focus Manual Input
        manualInput.focus();
        manualInput.select();

        // Clear results
        resultsContainer.innerHTML = `
            <div class="text-center py-8">
                <p class="text-gray-400 mb-2">Code <span class="text-white font-mono">${data.keyword}</span> not found.</p>
                <p class="text-sm text-gray-500">Please type a product name (e.g. "레깅스")</p>
            </div>
        `;
    } else {
        // Manual search failed
        searchHint.textContent = "No results found.";
        resultsContainer.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                No results for "${data.keyword}"
            </div>
        `;
    }

    // Allow re-scan after delay
    setTimeout(() => { scanCooldown = false; }, 2000);
}

function renderResults(products) {
    resultsContainer.innerHTML = '';

    products.forEach(product => {
        const el = document.createElement('div');
        el.className = "bg-gray-800 rounded-lg p-4 flex justify-between items-center border border-gray-700 animate-fade-in";
        el.innerHTML = `
            <div class="flex-1 pr-4">
                <h3 class="font-medium text-white text-sm line-clamp-2">${product.product_name}</h3>
                <a href="${product.product_url}" target="_blank" class="text-xs text-blue-400 mt-1 hover:underline">View on Andar</a>
            </div>
            <div class="text-right whitespace-nowrap">
                <span class="block text-red-400 font-bold text-lg">${product.sale_price}</span>
                ${product.original_price !== product.sale_price ? `<span class="block text-xs text-gray-500 line-through">${product.original_price}</span>` : ''}
            </div>
        `;
        resultsContainer.appendChild(el);
    });
}

// Manual Event Listeners
searchBtn.addEventListener('click', () => {
    performSearch(manualInput.value, false);
});

manualInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        performSearch(manualInput.value, false);
    }
});

// Start
init();
