import os
import csv
import time
from datetime import datetime
import socketio

sio = socketio.Client()
SPACE_ID = "86fb9e11-6795-4e98-ac36-67262d509fc6"
CSV_FILE = "occupancy_log.csv"

occupants = None
max_capacity = 1000

@sio.event
def connect():
    sio.emit('manualoccupancy:subscribe', SPACE_ID)
    sio.emit('manualoccupancy:spaceupdate-subscribe', SPACE_ID)

@sio.on('manualoccupancy:data')
def on_data(data):
    global occupants
    if isinstance(data, dict) and 'occupants' in data:
        occupants = int(data['occupants'])

@sio.on('manualoccupancy:spaceupdate')
def on_spaceupdate(data):
    global max_capacity
    if isinstance(data, dict) and 'space' in data:
        max_capacity = int(data['space'].get('maxCapacity', max_capacity))

def log_data():
    try:
        sio.connect('https://app.safespace.io', socketio_path='/veart/socket.io', timeout=10)
        
        # Wait up to 10 seconds for the server to return occupancy data
        for _ in range(20):
            if occupants is not None:
                break
            time.sleep(0.5)
            
        sio.disconnect()
    except Exception as e:
        print(f"Connection error: {e}")

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
