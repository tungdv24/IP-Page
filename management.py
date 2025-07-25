import sqlite3

DB_FILE = "network_monitor.db"

def list_ip_ranges():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, cidr FROM ip_ranges")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No IP ranges found.")
    else:
        print(f"{'ID':<5} {'Name':<20} {'CIDR'}")
        print("-" * 40)
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<20} {row[2]}")

def delete_ip_range(range_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Confirm the range exists
    cursor.execute("SELECT name, cidr FROM ip_ranges WHERE id = ?", (range_id,))
    row = cursor.fetchone()
    if not row:
        print(f"❌ Range with ID {range_id} not found.")
        conn.close()
        return

    # Delete the range
    cursor.execute("DELETE FROM ip_ranges WHERE id = ?", (range_id,))
    conn.commit()
    conn.close()
    print(f"✅ Deleted IP range '{row[0]}' ({row[1]}) and associated IPs.")

def main():
    while True:
        print("\n--- IP Range Management ---")
        print("1. List IP ranges")
        print("2. Delete an IP range")
        print("3. Exit")
        choice = input("Select an option: ").strip()

        if choice == "1":
            list_ip_ranges()
        elif choice == "2":
            range_id = input("Enter the ID of the IP range to delete: ").strip()
            if range_id.isdigit():
                delete_ip_range(int(range_id))
            else:
                print("⚠️ Invalid ID format.")
        elif choice == "3":
            print("Bye.")
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
