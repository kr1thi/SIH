from flask import Flask, request, jsonify
import hashlib
import sqlite3
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__)

# Enable CORS for all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Database setup
def get_db_connection():
    conn = sqlite3.connect('downloads.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Download (
            id INTEGER PRIMARY KEY,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_hash TEXT UNIQUE NOT NULL,
            data_hash TEXT UNIQUE NOT NULL,
            location TEXT NOT NULL,
            download_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def calculate_file_hash(file_content):
    """Calculate the SHA-256 hash of the file content."""
    hash_algo = hashlib.sha256()
    hash_algo.update(file_content)
    return hash_algo.hexdigest()

def calculate_hash_from_file_path(file_path):
    """Calculate the SHA-256 hash of a file stored locally on the system."""
    hash_algo = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):  # Read the file in chunks
            hash_algo.update(chunk)
    return hash_algo.hexdigest()

@app.route('/check_download', methods=['POST'])
def check_download():
    """
    Check if a file is a duplicate by recalculating the hash using the file stored in the location.
    If the recalculated hash matches, it's a duplicate. If not, update the stored hash.
    """
    data = request.json
    file_name = data.get('fileName')
    file_size = data.get('fileSize')
    file_url = data.get('fileUrl')

    # Download the file content from the URL
    response = requests.get(file_url)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to download the file'}), 400
    file_content = response.content
    #print(f"file content : {file_content}")
    # Calculate the hash of the downloaded file
    endpoint_hash = calculate_file_hash(file_content)
    print(f"end point : {endpoint_hash}")
    conn = get_db_connection()
    c = conn.cursor()

    # Check if the hash already exists in the database
    c.execute('SELECT * FROM Download WHERE file_hash = ?', (endpoint_hash,))
    existing_file = c.fetchone()

    if existing_file:
        # Recalculate the hash of the file stored in the location from the database
        local_file_path = existing_file['location']

        # Check if the file exists at the stored location
        if os.path.exists(local_file_path):
            # Calculate the hash of the file stored locally
            stored_data_hash = calculate_hash_from_file_path(local_file_path)
            print(f"database : {existing_file['data_hash']}")
            print(f"data_hash : {stored_data_hash}")
            # Compare the stored data hash with the newly calculated file hash
            if stored_data_hash == existing_file['data_hash']:
                # If hashes match, it's a duplicate
                duplicate_info = {
                    'duplicate': True,
                    'location': existing_file['location'],
                    'timestamp': existing_file['download_timestamp'],
                    'filename': existing_file['file_name']
                }
                conn.close()
                return jsonify(duplicate_info), 200
            else:
                # If the file hash in the local system is different from the database hash
                # Update the database with the new file hash and data hash
                #c.execute('UPDATE Download SET file_hash = ?, data_hash = ? WHERE id = ?', (endpoint_hash, stored_data_hash, existing_file['id']))
                conn.commit()
                conn.close()

                return jsonify({
                    'duplicate': False,
                    'message': 'File modified locally. Hash values updated in database.'
                }), 200
        else:
            # If the file does not exist at the stored location
            conn.close()
            return jsonify({'error': 'File not found at stored location'}), 404
    else:
        # No duplicate found based on the initial hash comparison
        conn.close()
        return jsonify({'duplicate': False}), 200

@app.route('/update_location', methods=['POST'])
def update_location():
    """
    Save the file download details including location and timestamp to the database.
    """
    data = request.json
    file_name = data.get('fileName')
    file_size = data.get('fileSize')
    file_url = data.get('fileUrl')
    location = data.get('location')

    # Download the file content
    response = requests.get(file_url)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to download the file'}), 400
    file_content = response.content

    # Calculate the hash of the downloaded file
    file_hash = calculate_file_hash(file_content)

    # Get current time for the download timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # For local time

    conn = get_db_connection()
    c = conn.cursor()

    # Check if the file already exists based on file_hash
    c.execute('SELECT * FROM Download WHERE file_hash = ?', (file_hash,))
    existing_file = c.fetchone()

    if existing_file:
        # Update the existing file record
        c.execute('''
            UPDATE Download
            SET file_name = ?, file_size = ?, location = ?, download_timestamp = ?
            WHERE file_hash = ?
        ''', (file_name, file_size, location, current_time, file_hash))
    else:
        # Insert a new file record
        # Calculate the hash of the file from its saved location
        data_hash = calculate_hash_from_file_path(location)

        c.execute('''
            INSERT INTO Download (file_name, file_size, file_hash, data_hash, location, download_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file_name, file_size, file_hash, data_hash, location, current_time))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(debug=True)
