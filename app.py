import pandas as pd
import numpy as np
from pyproj import Transformer

df = pd.read_excel('rotated_af.xlsx', sheet_name='clipped')

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

df['dist_to_prev_m'] = 0.0
for i in range(1, len(df)):
    df.loc[df.index[i], 'dist_to_prev_m'] = haversine(
        df.loc[df.index[i-1], 'latitude'], df.loc[df.index[i-1], 'longitude'],
        df.loc[df.index[i], 'latitude'], df.loc[df.index[i], 'longitude']
    )

transformer = Transformer.from_crs("EPSG:4326", "EPSG:32748")
df['utm_x'], df['utm_y'] = transformer.transform(df['latitude'], df['longitude'])

csv_data = df.to_csv(index=False)
with open('temp.csv', 'w') as f:
    f.write(csv_data)

print(csv_data[:1000]) # Print a snippet to verify