import pandas as pd
import math
import time
from pyproj import Transformer

# Configuration
REQUIRED_READINGS = 30

def calculate_slot(avg_lon, avg_lat):
    """
    Calculates the container slot using your rotation and UTM conversion logic.
    """
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32748", always_xy=True)
    ref_x, ref_y = transformer.transform(106.88171, -6.11249)
    utm_x, utm_y = transformer.transform(avg_lon, avg_lat)
    
    dx = utm_x - ref_x
    dy = utm_y - ref_y
    
    # Apply the 306-degree rotation
    angle_rad = math.radians(306)
    rot_x = dx * math.cos(angle_rad) + dy * math.sin(angle_rad)
    rot_y = -dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
    
    # Calculate Grid (6m x 2.5m containers)
    col_idx = math.floor(rot_x / 6.0)
    row_idx = math.floor(rot_y / 2.5)
    
    # Convert index to letter (A, B, C...)
    temp = col_idx
    col_letter = ""
    while temp >= 0:
        col_letter = chr((temp % 26) + 65) + col_letter
        temp = (temp // 26) - 1
        
    row_num = row_idx + 1 if row_idx >= 0 else row_idx
    return f"{col_letter}{row_num}"

def main():
    print("--- STARTING OFFLINE SIMULATION ---")
    print("Loading data from 'distance_to_meter and utm_x utm_y.csv'...")
    
    try:
        df = pd.read_csv('distance_to_meter and utm_x utm_y.csv')
    except FileNotFoundError:
        print("Error: Could not find the CSV file. Make sure it is in the same folder.")
        return

    # Shuffle the data to simulate random movement within your bounds
    df = df.sample(frac=1).reset_index(drop=True)
    
    counter = 0
    lon_sum = 0.0
    lat_sum = 0.0
    
    # Loop through the rows to mimic incoming serial data
    for index, row in df.iterrows():
        lon_val = row['longitude']
        lat_val = row['latitude']
        
        lon_sum += lon_val
        lat_sum += lat_val
        counter += 1
        
        print(f"Incoming Signal {counter}/{REQUIRED_READINGS}: {lon_val:.6f}, {lat_val:.6f}")
        time.sleep(0.1) # Small delay to make it feel like real GPS reading
        
        if counter == REQUIRED_READINGS:
            avg_lon = lon_sum / REQUIRED_READINGS
            avg_lat = lat_sum / REQUIRED_READINGS
            
            slot = calculate_slot(avg_lon, avg_lat)
            
            print("\n" + "="*30)
            print(" BATCH COMPLETE (30 READINGS)")
            print("="*30)
            print(f"Average Longitude : {avg_lon:.6f}")
            print(f"Average Latitude  : {avg_lat:.6f}")
            print(f"Target Slot       : {slot}")
            print("="*30 + "\n")
            
            # Stop after finding one complete batch for the simulation
            break

if __name__ == '__main__':
    main()