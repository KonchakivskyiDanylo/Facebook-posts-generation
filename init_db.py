import sqlite3

DB_PATH = 'facebook_posts_data.db'

def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create topics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    # Optional: Insert default topics
    cursor.executemany(
        "INSERT INTO topics (name) VALUES (?)",
        [('Automotive News',), ('EV Trends',), ('Maintenance Tips',)]
    )

    conn.commit()
    conn.close()
    print("Database initialized and topics table created.")

if __name__ == "__main__":
    initialize_database()
