# backend/app/serial_bridge.py
import asyncio
import serial
import json
import requests
import time

SERIAL_PORT = "/dev/tty.usbserial-120"   # adjust to your Arduino port
BAUD_RATE = 9600
BACKEND_URL = "http://127.0.0.1:8000"
OPEN_RETRY_DELAY = 2.0

serial_queue = asyncio.Queue()


async def write_to_serial(message: str):
    """Put a message into the queue to be sent to Arduino.
    Awaitable so routes can `await write_to_serial(...)`.
    """
    await serial_queue.put(message if message.endswith("\n") else message + "\n")


def send_to_backend(endpoint: str, data: dict = None):
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if data is not None:
            r = requests.post(url, json=data, timeout=5)
        else:
            r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"[WARN] Backend request failed for {endpoint}: {e}")
        return None


async def serial_writer(ser: serial.Serial):
    while True:
        msg = await serial_queue.get()
        try:
            ser.write(msg.encode())
            print(f"[TX → Arduino] {msg.strip()}")
        except Exception as e:
            print(f"[ERROR] Failed to write to serial: {e}")
        await asyncio.sleep(0)  # yield


async def serial_reader(ser: serial.Serial):
    loop = asyncio.get_running_loop()
    while True:
        try:
            # non-blocking check
            if ser.in_waiting > 0:
                raw = ser.readline()
                try:
                    line = raw.decode("utf-8", errors="ignore").strip()
                except Exception:
                    line = raw.decode("latin1", errors="ignore").strip()
                if not line:
                    continue
                print(f"[RX ← Arduino] {line}")

                # handle messages from Arduino
                if line == "START_DISPENSE":
                    # Arduino requested backend start (if needed)
                    result = send_to_backend("/start-dispense")
                    if result and "job_id" in result:
                        job_id = result["job_id"]
                        ser.write(f"JOB_ID:{job_id}\n".encode())
                        print(f"[→ Arduino] JOB_ID:{job_id}")

                elif line.startswith("DISPENSE_DONE:"):
                    job_id = line.split(":", 1)[1].strip()
                    send_to_backend(f"/dispense-complete/{job_id}")

                elif line.startswith("STATUS_REQ:"):
                    job_id = line.split(":", 1)[1].strip()
                    status = send_to_backend(f"/dispense-status/{job_id}")
                    if status:
                        msg = json.dumps(status)
                        ser.write((msg + "\n").encode())

                else:
                    # optional: forward any debug lines to backend or just print
                    pass
            else:
                await asyncio.sleep(0.05)
        except Exception as e:
            print(f"[ERROR] Serial read loop exception: {e}")
            await asyncio.sleep(0.5)


async def open_serial():
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"[INFO] Connected to Arduino on {SERIAL_PORT}")
            # small delay to let Arduino boot and print ARDUINO_CONNECTED
            await asyncio.sleep(1.5)
            return ser
        except Exception as e:
            print(f"[ERROR] Unable to open serial port '{SERIAL_PORT}': {e}")
            print(f"[INFO] Retrying in {OPEN_RETRY_DELAY}s...")
            await asyncio.sleep(OPEN_RETRY_DELAY)


async def main():
    while True:
        ser = await open_serial()
        try:
            # start reader and writer tasks
            reader = asyncio.create_task(serial_reader(ser))
            writer = asyncio.create_task(serial_writer(ser))
            done, pending = await asyncio.wait(
                [reader, writer], return_when=asyncio.FIRST_EXCEPTION
            )
            # if we exit, cancel pending
            for p in pending:
                p.cancel()
        except Exception as e:
            print(f"[ERROR] Serial bridge main loop exception: {e}")
        finally:
            try:
                ser.close()
            except Exception:
                pass
            print("[INFO] Serial connection closed, will attempt reopen.")
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
