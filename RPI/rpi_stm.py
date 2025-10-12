#!/usr/bin/env python3
"""
Simple STM-Raspberry Pi communication test.
Connects via USB serial and lets you send/receive messages interactively. Hosted on RPI
"""

import serial
import threading
import time

# --- CONFIGURE THIS ---
PORT = "/dev/ttyACM0"   # check with: ls /dev/ttyACM*
BAUD = 115200
# -----------------------

def read_from_stm(ser):
    """Continuously read from STM and print output."""
    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                print(f"[STM → RPi] {line}")
        except Exception as e:
            print(f"[ERROR reading STM] {e}")
            break

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)  # allow connection to stabilize
        print(f"✅ Connected to STM on {PORT} @ {BAUD}")
    except Exception as e:
        print(f"❌ Failed to connect to STM: {e}")
        return

    # Start listener thread
    threading.Thread(target=read_from_stm, args=(ser,), daemon=True).start()

    print("\nType messages to send to STM. Type 'exit' to quit.\n")
    while True:
        msg = input("[RPi → STM] > ")
        if msg.lower() in ("exit", "quit"):
            break
        try:
            ser.write((msg + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[ERROR sending to STM] {e}")
            break

    ser.close()
    print("🔌 Disconnected.")

if __name__ == "__main__":
    main()
