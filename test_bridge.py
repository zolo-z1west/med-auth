from backend.app.serial_bridge import write_to_serial
import asyncio
asyncio.run(write_to_serial("DISPENSE:OK:123\n"))
