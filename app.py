import sqlite3
import ipaddress
import os
import time
import threading
import requests
from ping3 import ping
from flask import Flask, render_template, jsonify, request
import concurrent.futures

from database import (
    save_ip_status,
    fetch_ip_status,
    add_ip_range,
    get_ranges,
    get_blacklist,
    add_to_blacklist,
    remove_from_blacklist
)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

down_since = {}

# Initially load blacklist
SKIP_ALERT_IPS = get_blacklist()

def update_ip_status(ip, new_status, range_id):
    global down_since
    conn = sqlite3.connect('network_monitor.db')
    cursor = conn.cursor()

    cursor.execute("SELECT status, tag FROM ip_status WHERE ip = ?", (ip,))
    result = cursor.fetchone()

    previous_status = result[0] if result else None
    tag = result[1] if result and result[1] else ""

    current_time = time.time()

    if new_status == "DOWN":
        if ip not in down_since:
            down_since[ip] = current_time
            conn.close()
            return
        elif current_time - down_since[ip] < 15:
            conn.close()
            return
    else:
        down_since.pop(ip, None)

    if previous_status != new_status:
        if ip in SKIP_ALERT_IPS:
            print(f"[INFO] Skipping alert for {ip} (status changed to {new_status})")
        else:
            icon = "✅" if new_status == "UP" else "🔴"
            log_message = f"{icon} {tag} - {ip} - Status changed to {new_status}" if tag else f"{icon} {ip} - Status changed to {new_status}"
            print(log_message)
            send_telegram_message(log_message)

        if previous_status is None:
            cursor.execute(
                "INSERT INTO ip_status (ip, status, range_id, tag) VALUES (?, ?, ?, ?)",
                (ip, new_status, range_id, tag)
            )
        else:
            cursor.execute(
                "UPDATE ip_status SET status = ? WHERE ip = ?",
                (new_status, ip)
            )

        conn.commit()

    conn.close()


def load_blacklist_periodically():
    global SKIP_ALERT_IPS
    while True:
        SKIP_ALERT_IPS = get_blacklist()
        time.sleep(10)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def check_ip(ip):
    response = ping(ip, timeout=1)
    return response is not None

def monitor_ip_ranges():
    while True:
        ranges = get_ranges()
        for r in ranges:
            ip_range = ipaddress.IPv4Network(r['cidr'], strict=False)
            check_ip_range(ip_range, r['id'])
        time.sleep(10)

def check_ip_range(ip_range, range_id):
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_ip, str(ip)): str(ip) for ip in sorted(ip_range.hosts())}
        for future in concurrent.futures.as_completed(futures):
            ip_str = futures[future]
            allocated = future.result()
            status = "UP" if allocated else "DOWN"
            update_ip_status(ip_str, status, range_id)

@app.route('/', methods=['GET'])
def home():
    ranges = get_ranges()
    return render_template(
        'home.html',
        ranges=sorted(ranges, key=lambda x: ipaddress.IPv4Network(x['cidr']).network_address)
    )

@app.route('/dashboard/<range_id>', methods=['GET'])
def get_ip_status(range_id):
    ranges = get_ranges()
    selected_range = next((r for r in ranges if str(r['id']) == str(range_id)), None)

    if selected_range is None:
        return "Range not found", 404

    ip_status = sorted(fetch_ip_status(range_id), key=lambda x: ipaddress.IPv4Address(x['ip']))

    for ip in ip_status:
        ip["tag"] = ip["tag"] if ip["tag"] else ""

    return render_template(
        'dashboard.html',
        rows=ip_status,
        range_name=selected_range['name'],
        range_id=range_id
    )

@app.route('/add_range', methods=['POST'])
def add_range():
    data = request.json
    name = data["name"]
    cidr = data["cidr"]
    add_ip_range(name, cidr)
    return jsonify({"success": True})

@app.route('/update_tags', methods=['POST'])
def update_tags():
    try:
        data = request.json
        conn = sqlite3.connect('network_monitor.db')
        cursor = conn.cursor()

        for ip, tag in data.items():
            if ipaddress.ip_address(ip) in ipaddress.ip_network("192.168.10.0/24", strict=False):
                cursor.execute("UPDATE ip_status SET tag = ? WHERE ip = ?", (tag, ip))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Tags updated successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/blacklist', methods=['GET'])
def view_blacklist():
    return jsonify(sorted(list(SKIP_ALERT_IPS)))

@app.route('/blacklist', methods=['POST'])
def add_blacklist():
    ip = request.json.get("ip")
    if not ip:
        return jsonify({"success": False, "message": "No IP specified"}), 400
    add_to_blacklist(ip)
    return jsonify({"success": True, "message": f"{ip} added to blacklist"})

@app.route('/blacklist', methods=['DELETE'])
def remove_blacklist():
    ip = request.json.get("ip")
    if not ip:
        return jsonify({"success": False, "message": "No IP specified"}), 400
    remove_from_blacklist(ip)
    return jsonify({"success": True, "message": f"{ip} removed from blacklist"})

if __name__ == '__main__':
    threading.Thread(target=load_blacklist_periodically, daemon=True).start()
    threading.Thread(target=monitor_ip_ranges, daemon=True).start()
    app.run(host='0.0.0.0', port=20000)