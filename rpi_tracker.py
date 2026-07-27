import serial
import math
import datetime
from pyproj import Transformer
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# --- CONFIGURATION ---
PORT = '/dev/ttyACM0'
BAUD = 115200
REQUIRED_READINGS = 30
DRIVE_FOLDER_ID = 'YOUR_GOOGLE_DRIVE_FOLDER_ID' # Replace with your actual folder ID

def nmea_to_decimal(value, direction):
    """
    Converts raw NMEA coordinates (e.g. 10652.9026) into standard decimal degrees (106.88171).
    """
    if not value: return 0.0
    
    # Find the decimal point to separate degrees and minutes
    dot_idx = value.find('.')
    if dot_idx == -1: return 0.0
    
    degrees = float(value[:dot_idx-2])
    minutes = float(value[dot_idx-2:])
    
    # Formula: Degrees + (Minutes / 60)
    decimal = degrees + (minutes / 60.0)
    
    # South and West are negative values
    if direction in ['S', 'W']:
        decimal = -decimal
        
    return decimal

def calculate_slot(avg_lon, avg_lat):
    """
    Recreates your Javascript mapping logic in Python to find the container slot.
    """
    # 1. Convert to UTM Zone 48S
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32748", always_xy=True)
    ref_x, ref_y = transformer.transform(106.88171, -6.11249)
    utm_x, utm_y = transformer.transform(avg_lon, avg_lat)
    
    dx = utm_x - ref_x
    dy = utm_y - ref_y
    
    # 2. Apply the 306-degree rotation 
    angle_rad = math.radians(306)
    rot_x = dx * math.cos(angle_rad) + dy * math.sin(angle_rad)
    rot_y = -dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
    
    # 3. Find Grid Coordinates
    c_length = 6.0
    c_width = 2.5
    col_idx = math.floor(rot_x / c_length)
    row_idx = math.floor(rot_y / c_width)
    
    # Convert column index to letters (0 = A, 1 = B, etc.)
    temp = col_idx
    col_letter = ""
    while temp >= 0:
        col_letter = chr((temp % 26) + 65) + col_letter
        temp = (temp // 26) - 1
        
    row_num = row_idx + 1 if row_idx >= 0 else row_idx
    return f"{col_letter}{row_num}"

def upload_to_drive(result_text):
    """
    Uploads a simple text file to Google Drive. 
    Note: You must set up Google Cloud OAuth and place 'client_secrets.json' in this folder.
    """
    try:
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth() # Opens a browser to log in on the first run
        drive = GoogleDrive(gauth)
        
        # Create a unique filename with the current time
        filename = f"Slot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        new_file = drive.CreateFile({'title': filename, 'parents': [{'id': DRIVE_FOLDER_ID}]})
        
        new_file.SetContentString(result_text)
        new_file.Upload()
        print(f"Success: Uploaded {filename} to Google Drive.")
    except Exception as e:
        print("Upload Skipped: Please configure Google Drive credentials first.", e)

def main():
    # Connect to the GPS module
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print("Connected to Ardusimple GPS. Waiting for RTK Fixed data...")
    
    counter = 0
    lon_sum = 0.0
    lat_sum = 0.0
    alt_sum = 0.0
    
    while True:
        # Read the line from the serial port and clean it up
        line = ser.readline().decode('ascii', errors='ignore').strip()
        
        if line.startswith('$GNGGA'):
            parts = line.split(',')
            
            # Ensure the NMEA string is complete before trying to read it
            if len(parts) < 10:
                continue
                
            fix_quality = parts[6]
            
            # Condition: If Fix Status is 4 (RTK Fixed)
            if fix_quality == '4':
                lon_val = nmea_to_decimal(parts[4], parts[5])
                lat_val = nmea_to_decimal(parts[2], parts[3])
                
                # Check if altitude is empty before converting to float
                alt_val = float(parts[9]) if parts[9] else 0.0
                
                lon_sum += lon_val
                lat_sum += lat_val
                alt_sum += alt_val
                counter += 1
                
                print(f"Reading {counter}/{REQUIRED_READINGS} recorded (RTK Fixed)")
                
                # Completion: Once we hit exactly 30 readings
                if counter == REQUIRED_READINGS:
                    avg_lon = lon_sum / REQUIRED_READINGS
                    avg_lat = lat_sum / REQUIRED_READINGS
                    avg_alt = alt_sum / REQUIRED_READINGS
                    
                    slot = calculate_slot(avg_lon, avg_lat)
                    
                    output_msg = (
                        f"Calculated Container Position:\n"
                        f"Longitude: {avg_lon:.6f}\n"
                        f"Latitude: {avg_lat:.6f}\n"
                        f"Altitude: {avg_alt:.2f} m\n"
                        f"Container Slot: {slot}"
                    )
                    
                    print("\n--- BATCH COMPLETE ---")
                    print(output_msg)
                    print("----------------------\n")
                    
                    upload_to_drive(output_msg)
                    
                    # Reset the arrays and counter for the next batch
                    counter = 0
                    lon_sum, lat_sum, alt_sum = 0.0, 0.0, 0.0
                    
            # Reset Condition: If any reading is NOT RTK Fixed
            else:
                if counter > 0:
                    print(f"Status dropped to {fix_quality}. Resetting counter to 0.")
                    counter = 0
                    lon_sum, lat_sum, alt_sum = 0.0, 0.0, 0.0

if __name__ == '__main__':
    main()