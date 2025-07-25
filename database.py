import sqlite3
import time

def initialize_database():
    conn = sqlite3.connect("network_monitor.db")
    cursor = conn.cursor()
    
    # Create ip_ranges table to store different ranges
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_ranges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cidr TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create ip_status table to store IP addresses, their status, and tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL UNIQUE,
            status TEXT CHECK(status IN ('UP', 'DOWN')) NOT NULL,
            tag TEXT,
            range_id INTEGER,
            FOREIGN KEY(range_id) REFERENCES ip_ranges(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def save_ip_status(ip, status, range_id, tag=None):
    conn = sqlite3.connect("network_monitor.db")
    cursor = conn.cursor()
    
    # Check if IP already exists
    cursor.execute("SELECT status FROM ip_status WHERE ip = ?", (ip,))
    result = cursor.fetchone()
    
    if result:
        old_status = result[0]
        if old_status != status:
            print(f"Status change detected: {ip} is now {status}")
            cursor.execute("UPDATE ip_status SET status = ?, tag = ? WHERE ip = ?", (status, tag, ip))
    else:
        cursor.execute("INSERT INTO ip_status (ip, status, tag, range_id) VALUES (?, ?, ?, ?)", (ip, status, tag, range_id))
    
    conn.commit()
    conn.close()

def fetch_ip_status(range_id):
    conn = sqlite3.connect("network_monitor.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ip, status, tag FROM ip_status WHERE range_id = ?", (range_id,))
    data = cursor.fetchall()
    conn.close()
    return [{"ip": row[0], "status": row[1], "tag": row[2]} for row in data]

def add_ip_range(name, cidr):
    conn = sqlite3.connect("network_monitor.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ip_ranges (name, cidr) VALUES (?, ?)", (name, cidr))
    conn.commit()
    conn.close()

def get_ranges():
    conn = sqlite3.connect("network_monitor.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, cidr FROM ip_ranges")
    ranges = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "cidr": row[2]} for row in ranges]

def get_blacklist():
    conn = sqlite3.connect('network_monitor.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS blacklist (ip TEXT PRIMARY KEY)")
    cursor.execute("SELECT ip FROM blacklist")
    rows = cursor.fetchall()
    conn.close()
    return set(row[0] for row in rows)

def add_to_blacklist(ip):
    conn = sqlite3.connect('network_monitor.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO blacklist (ip) VALUES (?)", (ip,))
    conn.commit()
    conn.close()

def remove_from_blacklist(ip):
    conn = sqlite3.connect('network_monitor.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE ip = ?", (ip,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
    