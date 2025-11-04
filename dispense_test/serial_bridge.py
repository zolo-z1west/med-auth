import serial
import time

SERIAL_PORT = "/dev/cu.usbserial-10"  # replace with your Arduino port
BAUD = 9600

try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
    print(f"Python bridge: opened {SERIAL_PORT}")
    time.sleep(1)  # small delay to let Arduino initialize
except Exception as e:
    print("Failed to open serial:", e)
    exit(1)

# Optional: send a test command if Arduino needs it
ser.write(b'DISPENSE;dose;user\n')
ser.flush()
print("Python bridge: sent TEST command")

# Keep script alive just to hold serial connection
while True:
    time.sleep(1)
