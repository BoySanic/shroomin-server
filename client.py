import time
import json
import requests
import sys

# Configuration
SEEDS_FILE = "output.txt"
SERVER_URL = "https://shroomweb.0xa.pw"  # Change to your server URL
POLL_INTERVAL = 5  # seconds between checks
API_KEY = sys.argv[1]
SMALL_BIOMES = sys.argv[2]
if(SMALL_BIOMES == "sb"):
    SERVER_URL += "/small_biomes"
else:
    SERVER_URL += "/large_biomes"
header = {
    'api-key': API_KEY
}
def parse_line(line):
    """Parse a line into a dictionary with seed, x, z, claimed_size."""
    parts = line.strip().split()
    if len(parts) != 4:
        return None
    try:
        return {
            "seed": int(parts[0]),
            "x": int(parts[1]),
            "z": int(parts[2]),
            "claimed_size": int(parts[3]),
        }
    except ValueError:
        return None

def main():
    last_position = 0
    print("Starting shroomin' client...")
    while True:
        try:
            print("Opening file...")
            with open(SEEDS_FILE, "r") as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()
            print(f"File opened. {len(new_lines)} entries.")
            if new_lines:

                parsed_data = []
                for line in new_lines:
                    parsed = parse_line(line)
                    if parsed:
                        parsed_data.append(parsed)
                    if len(parsed_data) == 10000 or len(new_lines) < 10000:
                        payload = {"data": parsed_data}
                        print("Sending payload:", json.dumps(payload, indent=2))
                        try:
                            response = requests.post(
                                SERVER_URL,
                                headers=header,
                                json=payload,
                                timeout=10
                            )
                            print("Server response:", response.status_code, response.text)
                        except requests.RequestException as e:
                            print("Error sending data:", e)
                        parsed_data = []
        except FileNotFoundError:
            print(f"File {SEEDS_FILE} not found. Waiting...")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()