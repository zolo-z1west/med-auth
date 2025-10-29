import serial
s = serial.Serial("/dev/tty.usbserial-120", 9600)
print("Opened:", s.name)
s.close()

