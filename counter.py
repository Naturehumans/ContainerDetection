import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pyproj import Transformer

# ==========================
# KONFIGURASI
# ==========================
ORIGIN_UTM_X = 708241.531
ORIGIN_UTM_Y = 9323986.322

SUDUT_ROTASI = -54
LEBAR_KOLOM = 2.5
PANJANG_BARIS = 6.0

JUMLAH_KOLOM = 12   # ubah sesuai jumlah kolom
JUMLAH_BARIS = 8    # ubah sesuai jumlah baris


def putar_titik(x, y, cx, cy, angle_deg):
    angle_rad = math.radians(angle_deg)

    tx = x - cx
    ty = y - cy

    rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
    ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)

    return rx + cx, ry + cy


def deteksi_blok(lon, lat):

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:32748",
        always_xy=True
    )

    utm_x, utm_y = transformer.transform(lon, lat)

    rot_x, rot_y = putar_titik(
        utm_x,
        utm_y,
        ORIGIN_UTM_X,
        ORIGIN_UTM_Y,
        SUDUT_ROTASI
    )

    jarak_x = rot_x - ORIGIN_UTM_X
    jarak_y = rot_y - ORIGIN_UTM_Y

    if jarak_x < 0 or jarak_y < 0:
        return None, rot_x, rot_y

    indeks_kolom = int(jarak_x // LEBAR_KOLOM)
    indeks_baris = int(jarak_y // PANJANG_BARIS)

    huruf = chr(65 + indeks_baris)
    angka = indeks_kolom + 1

    return (
        (indeks_baris, indeks_kolom, f"{huruf}{angka}"),
        rot_x,
        rot_y
    )


def gambar_grid(rot_x, rot_y, blok_info):

    fig, ax = plt.subplots(figsize=(12,8))

    # gambar grid
    for baris in range(JUMLAH_BARIS):

        for kolom in range(JUMLAH_KOLOM):

            x = kolom * LEBAR_KOLOM
            y = baris * PANJANG_BARIS

            warna = "white"

            if blok_info is not None:
                if baris == blok_info[0] and kolom == blok_info[1]:
                    warna = "gold"

            rect = Rectangle(
                (x, y),
                LEBAR_KOLOM,
                PANJANG_BARIS,
                facecolor=warna,
                edgecolor="black"
            )

            ax.add_patch(rect)

            label = f"{chr(65+baris)}{kolom+1}"

            ax.text(
                x + LEBAR_KOLOM/2,
                y + PANJANG_BARIS/2,
                label,
                ha='center',
                va='center',
                fontsize=8
            )

    # posisi titik
    px = rot_x - ORIGIN_UTM_X
    py = rot_y - ORIGIN_UTM_Y

    ax.scatter(
        px,
        py,
        color="red",
        s=120,
        zorder=5,
        label="Posisi GPS"
    )

    ax.text(
        px,
        py + 0.5,
        "GPS",
        color="red"
    )

    ax.set_xlim(0, JUMLAH_KOLOM * LEBAR_KOLOM)
    ax.set_ylim(0, JUMLAH_BARIS * PANJANG_BARIS)

    ax.set_aspect("equal")

    ax.set_xlabel("Meter (X)")
    ax.set_ylabel("Meter (Y)")
    ax.set_title("Visualisasi Grid Container")

    ax.grid(True)

    plt.legend()

    plt.show()


# ==========================
# MAIN
# ==========================

print("=== Program Deteksi Container ===")

input_lon = float(input("Longitude : "))
input_lat = float(input("Latitude  : "))

hasil, rot_x, rot_y = deteksi_blok(input_lon, input_lat)

if hasil is None:
    print("Titik berada di luar area.")
else:
    print(f"Container berada di Blok {hasil[2]}")

gambar_grid(rot_x, rot_y, hasil)