import hashlib

def calculate_sha256_hash(file_path):
    """Calculate the SHA-256 hash of a file located at file_path."""
    hash_algo = hashlib.sha256()  # Initialize SHA-256 hash algorithm
    
    try:
        with open(file_path, 'rb') as file:  # Open the file in binary mode
            while chunk := file.read(8192):
                #print(chunk)  # Read the file in chunks
                hash_algo.update(chunk)  # Feed each chunk into the hash algorithm
        return hash_algo.hexdigest()  # Return the final hash as a hexadecimal string
    except FileNotFoundError:
        return f"Error: The file at {file_path} was not found."
    except Exception as e:
        return f"Error: {str(e)}"

# Path to the file
file_path = r'C:\Users\BEST SOLUTION\Downloads\SampleDOCFile_200kb (1).doc'

# Calculate and print the hash
hash_value = calculate_sha256_hash(file_path)
print(f"SHA-256 Hash of the file: {hash_value}")
