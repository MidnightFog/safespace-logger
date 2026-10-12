import os
import csv
import json
import time
import re
from datetime import datetime
import requests

SPACE_ID = "86fb9e11-6795-4e98-ac36-67262d509fc6"
CSV_FILE = "occupancy_log.csv"
BASE_URL = "https://app.safespace.io/veart/socket.io/"

def extract_payload(text, event_name):
    target = f'"{event_name}",'
    idx = text.find(target)
    if idx == -1:
        return None
    start = text.find('{', idx)
    if start == -1:
        return None
    
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except Exception:
                    return None
    return None

def log_data():
    occupants = None
    max_capacity = 1000
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Referer": "https://app.safespace.io/api/display/live-occupancy/86fb9e11?view=percent"
    }
    
    try:
        # Step 1: Engine.IO Handshake
        res = session.get(f"{BASE_URL}?EIO=3&transport=polling", headers=headers, timeout=10)
        sid_match = re.search(r'"sid":"([^"]+)"', res.text)
        if not sid_match:
            print("Handshake failed:", res.text)
            return
        
        sid = sid_match.group(1)
        
        # Step 2: Send subscription messages
        msg1 = json.dumps(["manualoccupancy:subscribe", SPACE_ID])
        msg2 = json.dumps(["manualoccupancy:spaceupdate-subscribe", SPACE_ID])
        p1, p2 = f"42{msg1}", f"42{msg2}"
        payload = f"{len(p1)}:{p1}{len(p2)}:{p2}"
        
        session.post(f"{BASE_URL}?EIO=3&transport=polling&sid={sid}", data=payload, headers=headers, timeout=10)
        
        # Step 3: Poll for live occupancy data
        for _ in range(5):
            poll_res = session.get(f"{BASE_URL}?EIO=3&transport=polling&sid={sid}", headers=headers, timeout=10)
            p_text = poll_res.text
            
            data_payload = extract_payload(p_text, "manualoccupancy:data")
            if data_payload and "occupants" in data_payload:
                occupants = int(data_payload["occupants"])
                
            space_payload = extract_payload(p_text, "manualoccupancy:spaceupdate")
            if space_payload and "space" in space_payload and "maxCapacity" in space_payload["space"]:
                max_capacity = int(space_payload["space"]["maxCapacity"])
                
            if occupants is not None:
                break
                
            time.sleep(1)
            
    except Exception as e:
        print(f"Error fetching data: {e}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if occupants is not None:
        pct = round((occupants / max_capacity) * 100, 1)
        row = [timestamp, occupants, max_capacity, f"{pct}%"]
    else:
        row = [timestamp, "N/A", "N/A", "N/A"]

    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Occupants", "Max Capacity", "Occupancy %"])
        writer.writerow(row)
        
    print(f"Logged: {row}")

if __name__ == "__main__":
    log_data()
