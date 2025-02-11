document.addEventListener('DOMContentLoaded', function() {
    // Retrieve file information from storage
    chrome.storage.local.get('duplicateFile', function(data) {
        const file = data.duplicateFile;
        if (file) {
            document.getElementById('filename').textContent = `Filename: ${file.filename}`;
            document.getElementById('location').textContent = `Location: ${file.location}`;
            document.getElementById('timestamp').textContent = `Timestamp: ${file.timestamp}`;

            // Set up event listeners for buttons
            document.getElementById('redownload-btn').addEventListener('click', function() {
                console.log('Redownload button clicked');
                // Notify the background script to continue the download
                chrome.runtime.sendMessage({ action: 'redownload' });

                // Close the popup window after sending the message
                window.close();
            });

            document.getElementById('cancel-btn').addEventListener('click', function() {
                console.log('Cancel button clicked');
                // Notify the background script to cancel the download
                chrome.runtime.sendMessage({ action: 'cancelDownload' });

                // Close the popup window
                window.close();
            });
        }
    });
});
