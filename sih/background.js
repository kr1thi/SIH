// Function to perform fetch with retry logic and proper error handling
function fetchWithRetry(url, options, retries = 3, delay = 500, timeout = 30000) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Timeout exceeded')), timeout);

        fetch(url, options)
            .then(response => {
                clearTimeout(timer);
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => resolve(data))
            .catch(error => {
                clearTimeout(timer);
                if (retries > 0) {
                    console.warn(`Fetch failed, retrying in ${delay}ms... (${retries} retries left)`);
                    setTimeout(() => fetchWithRetry(url, options, retries - 1, delay * 2, timeout).then(resolve).catch(reject), delay);
                } else {
                    reject(error);
                }
            });
    });
}

// Store the current popup window ID and pending download ID
let popupWindowId = null;
let pendingDownloadId = null;
let pendingDownloadUrl = null;
let pendingDownloadFilename = null;

// Intercept downloads and check for duplicates
chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
    const downloadId = downloadItem.id;
    const filename = downloadItem.filename;
    const fileSize = downloadItem.fileSize;
    const fileUrl = downloadItem.url;

    console.log(`Intercepting download for: ${filename}, ID: ${downloadId}`);

    // Fetch file details from the backend to check for duplicates
    fetchWithRetry('http://localhost:5000/check_download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            fileName: filename,
            fileSize: fileSize,
            fileUrl: fileUrl
        })
    })
    .then(data => {
        console.log('Received response data:', data);

        if (data.duplicate) {
            console.log('Duplicate file detected. Showing custom popup...');

            // Store information to be used later
            pendingDownloadId = downloadId;
            pendingDownloadUrl = fileUrl;
            pendingDownloadFilename = filename;

            // Open the custom popup
            chrome.windows.create({
                url: 'popup.html',
                type: 'popup',
                width: 400,
                height: 200,
                left: 100,
                top: 100
            }, function (window) {
                popupWindowId = window.id; // Store the popup window ID

                console.log('Popup created with ID:', window.id);

                // Pass the download ID, filename, and other details to the popup
                chrome.storage.local.set({
                    duplicateFile: {
                        downloadId: downloadId,
                        filename: filename,
                        url: fileUrl,
                        location: data.location,
                        timestamp: data.timestamp
                    }
                });

                // Do not suggest the filename yet
                // This will prevent the Save As dialog from showing
            });

            // Return here to prevent the Save As dialog from showing
            return;
        }

        console.log('No duplicate found. Allowing download to proceed.');
        suggest({ filename: filename }); // Allow the download to proceed
    })
    .catch(error => {
        console.error('Fetch error:', error);
        suggest({ filename: filename }); // Allow the download to proceed if fetch fails
    });
});

// Add a listener to handle messages from the popup
chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
    if (request.action === 'redownload') {
        console.log('User chose to redownload.');
        if (popupWindowId) {
            // Close the popup.html
            chrome.windows.remove(popupWindowId, () => {
                // Resume the download with saveAs option
                chrome.downloads.download({ url: pendingDownloadUrl, filename: pendingDownloadFilename, saveAs: true }, (newDownloadId) => {
                    // Store the new download ID to track the re-download
                    pendingDownloadId = newDownloadId;
                    popupWindowId = null; // Clear the popup window ID
                    pendingDownloadUrl = null; // Clear the pending download URL
                    pendingDownloadFilename = null; // Clear the pending download filename
                });
            });
        }
    } else if (request.action === 'cancelDownload') {
        console.log('User chose to cancel download.');
        // Cancel the initial download
        if (pendingDownloadId) {
            chrome.downloads.cancel(pendingDownloadId, () => {
                console.log(`Download with ID ${pendingDownloadId} cancelled.`);
                pendingDownloadId = null; // Clear the pending download ID

                // Close the popup.html
                if (popupWindowId) {
                    chrome.windows.remove(popupWindowId, () => {
                        console.log(`Popup with ID ${popupWindowId} closed.`);
                        popupWindowId = null; // Clear the popup window ID
                    });
                }
            });
        } else {
            // Close the popup.html if no pending download ID is available
            if (popupWindowId) {
                chrome.windows.remove(popupWindowId, () => {
                    console.log(`Popup with ID ${popupWindowId} closed.`);
                    popupWindowId = null; // Clear the popup window ID
                });
            }
        }
    }
});

// Listener to handle download completion
chrome.downloads.onChanged.addListener((delta) => {
    if (delta.state && delta.state.current === 'complete' && delta.id) {
        chrome.downloads.search({ id: delta.id }, (results) => {
            const downloadItem = results[0];
            const location = downloadItem.filename;

            console.log(`File downloaded to: ${location}`);

            // Send the filename and location to backend
            fetchWithRetry('http://localhost:5000/update_location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    fileName: downloadItem.filename,
                    fileSize: downloadItem.fileSize,
                    fileUrl: downloadItem.url,
                    location: location
                })
            }).catch(error => console.error('Fetch error:', error));
        });
    }
});
