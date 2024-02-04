import asyncio

from inverter import Inverter


async def main():
    myInverter = Inverter("adrlpi01.adrlab.xyz", 8002)

    print(f"Model: {myInverter.model}")
    print(f"Serial number: {myInverter.serial_number}")

    running_info = await myInverter.get_running_info()

    print(running_info)


asyncio.run(main())
