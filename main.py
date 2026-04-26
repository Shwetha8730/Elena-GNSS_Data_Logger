import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import traceback
import csv

# Globals
info_last_update_time = 0
last_update_time = 0
is_reading = False
parsed_data_list = []

# Utility functions
def format_time(raw_time):
    if not raw_time or len(raw_time) < 6:
        return "--"
    return f"{raw_time[:2]}:{raw_time[2:4]}:{raw_time[4:6]}"

def convert_to_decimal(degree_min, direction):
    if not degree_min or not direction:
        return None
    try:
        if direction in ['N', 'S']:
            degrees = float(degree_min[:2])
            minutes = float(degree_min[2:])
        else:
            degrees = float(degree_min[:3])
            minutes = float(degree_min[3:])
        decimal = degrees + minutes / 60
        if direction in ['S', 'W']:
            decimal *= -1
        return round(decimal, 6)
    except:
        return None

def set_status(color, text):
    status_indicator.config(bg=color)
    status_label.config(text=text)

def export_to_csv():
    if not parsed_data_list:
        set_status("red", "No data yet!")
        return
    filename = "gnss_export.csv"
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Timestamp", "Latitude", "Longitude", "Altitude", "Satellites"])
            writer.writeheader()
            writer.writerows(parsed_data_list)
        set_status("green", "CSV Saved!")
    except Exception:
        traceback.print_exc()
        set_status("red", "Export Failed!")

def read_from_file(filename):
    global is_reading, last_update_time, info_last_update_time
    gps_data, navic_data, glonass_data = [], [], []

    root.after(0, lambda: set_status("yellow", "Reading..."))

    try:
        with open(filename, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if not is_reading:
                break
            line = line.strip()
            if not line:
                continue

            nmea_log.insert(tk.END, line + "\n")
            nmea_log.see(tk.END)
            fields = line.split(',')
            current_time = time.time()

            if line.startswith(('$GPGSV', '$GLGSV', '$GAGSV', '$BDGSV')):
                for i in range(4, len(fields) - 4, 4):
                    try:
                        prn = fields[i]
                        snr = fields[i + 3]
                        if prn and snr:
                            snr_val = int(snr)
                            prn_val = str(prn)
                            if line.startswith('$GPGSV'):
                                gps_data.append((prn_val, snr_val))
                            elif line.startswith('$GAGSV'):
                                navic_data.append((prn_val, snr_val))
                            elif line.startswith('$GLGSV'):
                                glonass_data.append((prn_val, snr_val))
                    except:
                        continue

                try:
                    sat_view = fields[3]
                    info_labels["Satellites in View"].config(text=sat_view)
                except:
                    pass

            if current_time - info_last_update_time >= 1:
                if line.startswith(('$GPGGA', '$GNGGA')) and len(fields) >= 15:
                    timestamp = fields[1]
                    lat = convert_to_decimal(fields[2], fields[3])
                    lon = convert_to_decimal(fields[4], fields[5])
                    altitude = fields[9]
                    satellites = fields[7]

                    info_labels["Timestamp"].config(text=format_time(timestamp))
                    info_labels["Latitude"].config(text=f"{lat}° {fields[3]}" if lat is not None else "--")
                    info_labels["Longitude"].config(text=f"{lon}° {fields[5]}" if lon is not None else "--")
                    info_labels["Altitude"].config(text=f"{altitude} m" if altitude else "--")
                    info_labels["Satellites Tracked"].config(text=satellites)

                    if lat and lon:
                        parsed_data_list.append({
                            "Timestamp": format_time(timestamp),
                            "Latitude": lat,
                            "Longitude": lon,
                            "Altitude": altitude,
                            "Satellites": satellites
                        })

                elif line.startswith(('$GNGSA', '$GPGSA')) and len(fields) >= 18:
                    pdop = fields[15]
                    hdop = fields[16]
                    vdop = fields[17].split('*')[0]

                    info_labels["PDOP"].config(text=pdop if pdop else "--")
                    info_labels["HDOP"].config(text=hdop if hdop else "--")
                    info_labels["VDOP"].config(text=vdop if vdop else "--")

                info_last_update_time = current_time

            if current_time - last_update_time >= 1:
                if gps_data or navic_data or glonass_data:
                    update_snr_canvas(gps_data, navic_data, glonass_data)
                    gps_data.clear()
                    navic_data.clear()
                    glonass_data.clear()
                last_update_time = current_time

            time.sleep(0.05)

        if is_reading:
            root.after(0, lambda: set_status("green", "Completed!"))
        else:
            root.after(0, lambda: set_status("red", "Stopped"))

    except Exception:
        traceback.print_exc()
        root.after(0, lambda: set_status("red", "Error!"))

# GUI Setup
root = tk.Tk()
root.title("Elena GNSS Data Logger 7.1")
root.geometry("1400x700")
root.configure(bg="black")

PANEL_HEIGHT = 640
LEFT_WIDTH = 290
MIDDLE_WIDTH = 554
RIGHT_WIDTH = 500

main_frame = tk.Frame(root, bg="black")
main_frame.pack(fill="both", expand=True, padx=10, pady=10)

#Left Panel
left_panel = tk.Frame(main_frame, bg="black", width=LEFT_WIDTH, height=PANEL_HEIGHT)
left_panel.pack(side="left", padx=5, pady=5)
left_panel.pack_propagate(False)

tk.Label(left_panel, text="COM Port Setting", font=("Consolas", 13, "bold"),
         fg="white", bg="black").pack(pady=(5, 3))

comm_border = tk.Frame(left_panel, bg="black", highlightbackground="white", highlightthickness=2)
comm_border.pack(fill="x", padx=5)

def create_dropdown(parent, label, options, default):
    frame = tk.Frame(parent, bg="black")
    frame.pack(pady=4)
    tk.Label(frame, text=label, font=("Consolas", 12), fg="white",
             bg="black", width=10).pack(side="left", padx=5)
    combo = ttk.Combobox(frame, values=options, font=("Consolas", 11),
                         state="readonly", width=13)
    combo.set(default)
    combo.pack(side="left")
    return combo

com_port = create_dropdown(comm_border, "COM Port:", ["COM3"], "COM3")
baudrate = create_dropdown(comm_border, "Baudrate:", ["4800", "9600", "115200"], "9600")

# Status
status_frame = tk.Frame(comm_border, bg="black")
status_frame.pack(pady=5)
status_indicator = tk.Label(status_frame, bg="red", width=2, height=1)
status_indicator.pack(side="left", padx=8)
status_label = tk.Label(status_frame, text="Not Started",
                        font=("Consolas", 11), fg="white", bg="black")
status_label.pack(side="left")

# Buttons
btn_frame = tk.Frame(comm_border, bg="black")
btn_frame.pack(pady=5)

def start_serial_read():
    global is_reading
    if is_reading:
        set_status("yellow", "Already Running!")
        return
    is_reading = True
    parsed_data_list.clear()
    threading.Thread(target=read_from_file, args=("Nmea.txt",), daemon=True).start()

def disconnect_serial():
    global is_reading
    is_reading = False
    set_status("red", "Stopped")

def clear_nmea_log():
    nmea_log.delete(1.0, tk.END)

def on_refresh_click():
    global is_reading
    is_reading = False
    nmea_log.delete(1.0, tk.END)
    parsed_data_list.clear()
    for label in info_labels:
        info_labels[label].config(text="--")
    snr_canvas.delete("all")
    draw_legend()
    set_status("red", "Not Started")

ttk.Button(btn_frame, text="Connect", width=18,
           command=start_serial_read).pack(side="left", padx=4)
ttk.Button(btn_frame, text="Refresh", width=18,
           command=on_refresh_click).pack(side="left", padx=4)

row2 = tk.Frame(comm_border, bg="black")
row2.pack(pady=(4, 4))
ttk.Button(row2, text="Disconnect", width=18,
           command=disconnect_serial).pack(side="left", padx=4)
ttk.Button(row2, text="Clear Log", width=18,
           command=clear_nmea_log).pack(side="left", padx=4)

row3 = tk.Frame(comm_border, bg="black")
row3.pack(pady=(4, 8))
ttk.Button(row3, text="Export to CSV", width=38,
           command=export_to_csv).pack(padx=4)

# Info Panel
tk.Label(left_panel, text="Info Panel", font=("Consolas", 13, "bold"),
         fg="white", bg="black").pack(pady=(8, 3))

info_border = tk.Frame(left_panel, bg="black", highlightbackground="white",
                       highlightthickness=2)
info_border.pack(fill="both", expand=True, padx=5, pady=(0, 5))

info_labels = {}
data_panel = tk.Frame(info_border, bg="black")
data_panel.pack(padx=8, pady=10, fill="both", expand=True)

for label in ["Timestamp", "Latitude", "Longitude", "Altitude",
              "PDOP", "HDOP", "VDOP", "Satellites Tracked", "Satellites in View"]:
    row = tk.Frame(data_panel, bg="black")
    row.pack(fill="x", pady=6)
    tk.Label(row, text=f"{label}:", font=("Consolas", 11), fg="white",
             bg="black", width=19, anchor="w").pack(side="left")
    val_label = tk.Label(row, text="--", font=("Consolas", 11),
                         fg="white", bg="black", anchor="w")
    val_label.pack(side="left")
    info_labels[label] = val_label

# Middle Panel- SNR Chart
bar_frame = tk.Frame(main_frame, bg="black", width=MIDDLE_WIDTH, height=PANEL_HEIGHT)
bar_frame.pack(side="left", padx=5, pady=5)
bar_frame.pack_propagate(False)

tk.Label(bar_frame, text="PRN - SNR", font=("Consolas", 13, "bold"),
         fg="white", bg="black").pack(pady=(5, 3))

canvas_border = tk.Frame(bar_frame, bg="white", padx=2, pady=2)
canvas_border.pack()
snr_canvas = tk.Canvas(canvas_border, width=550, height=600,
                       bg="black", highlightthickness=0)
snr_canvas.pack()

def draw_legend():
    items = [("GPS", "red"), ("NavIC", "blue"), ("GLONASS", "magenta")]
    x_pos = [40, 220, 400]
    for i, (label, color) in enumerate(items):
        text_id = snr_canvas.create_text(x_pos[i], 10, text=label, fill="white",
                                         font=("Consolas", 13, "bold"), anchor="w")
        bbox = snr_canvas.bbox(text_id)
        snr_canvas.create_oval(bbox[2] + 10, 2, bbox[2] + 25, 17,
                               fill=color, outline=color)

def update_snr_canvas(gps_data, navic_data, glonass_data):
    snr_canvas.delete("all")
    draw_legend()
    MAX_ROWS = 12
    row_spacing = 45
    bar_width = 100
    bar_height = 20

    for idx in range(MAX_ROWS):
        y = 40 + idx * row_spacing
        for data, color, x_start in [
            (gps_data, "red", 40),
            (navic_data, "blue", 220),
            (glonass_data, "magenta", 400)
        ]:
            if idx < len(data):
                prn, snr = data[idx]
                snr_canvas.create_text(x_start - 10, y + 10, text=prn,
                                       fill="white", font=("Consolas", 10), anchor="e")
                if snr > 0:
                    snr_canvas.create_rectangle(x_start, y, x_start + snr * 2,
                                                y + bar_height, fill=color, outline="")
                snr_canvas.create_rectangle(x_start, y, x_start + bar_width,
                                            y + bar_height, outline="white")
                if snr > 0:
                    snr_canvas.create_text(x_start + bar_width + 10, y + 10,
                                           text=f"{snr}", fill="white",
                                           font=("Consolas", 9), anchor="w")

draw_legend()

# Right Panel - NMEA Log
log_frame = tk.Frame(main_frame, bg="black", width=RIGHT_WIDTH, height=PANEL_HEIGHT)
log_frame.pack(side="left", padx=5, pady=5)
log_frame.pack_propagate(False)

tk.Label(log_frame, text="NMEA Log", font=("Consolas", 13, "bold"),
         fg="white", bg="black").pack(pady=(5, 3))

log_border = tk.Frame(log_frame, bg="white", padx=2, pady=2)
log_border.pack(fill="both", expand=True)
nmea_log = scrolledtext.ScrolledText(log_border, bg="white", fg="black",
                                     font=("Consolas", 9))
nmea_log.pack(fill="both", expand=True)

root.mainloop()