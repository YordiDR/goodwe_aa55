import asyncio
import inverter
import time

async def main():
    myInverter = inverter.Inverter("adrlpi01.adrlab.xyz", 8002)

    print(f"Model: {myInverter.model}")
    print(f"Serial number: {myInverter.serial_number}")

    await myInverter.update_running_info()

    print(f"Work mode: {myInverter.work_mode_string}")
    print(f"Current feeding power: {myInverter.pac}")
    print(f"E today: {myInverter.e_today}")
    print(f"E total: {myInverter.e_total}")
    print(f"Line 1 Voltage: {myInverter.l1_voltage}")
    print(f"Line 1 Frequency: {myInverter.l1_frequency}")
    print(f"Total running hours: {myInverter.running_hours}")
    print(f"Temperature: {myInverter.temperature}")

asyncio.run(main())