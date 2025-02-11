import sqlite3

def view_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('downloads.db')
    conn.row_factory = sqlite3.Row  # Use Row factory to access columns by name

    # Create a cursor object to execute SQL queries
    c = conn.cursor()

    # Check if the Download table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Download'")
    table_exists = c.fetchone()

    if table_exists:
        # Table exists; proceed to retrieve data
        c.execute('SELECT * FROM Download')
        rows = c.fetchall()

        # Check if any data is returned
        if rows:
            # Dynamically get column names from the cursor description
            column_names = [description[0] for description in c.description]

            # Print column headers
            print(" | ".join(f"{col:<20}" for col in column_names))
            print('-' * (len(column_names) * 22))

            # Iterate through each row and print the data
            for row in rows:
                print(" | ".join(f"{str(row[col]):<20}" for col in column_names))
        else:
            print("No data found in the Download table.")
    else:
        print("The Download table does not exist in the database. Please ensure the database is initialized properly.")

    # Close the database connection
    conn.close()

# Call the function to view data
if __name__ == '__main__':
    view_data()
