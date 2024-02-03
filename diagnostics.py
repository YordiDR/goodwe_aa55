from .inverter import Inverter

inverter = Inverter("adrlpi01.adrlab.xyz", 8002)

print(f"Model: {inverter.model}")
print(f"Serial number: {inverter.serial_number}")

inverter.update_running_info()

print(f"Work mode: {inverter.work_mode_string}")
print(f"Current feeding power: {inverter.pac}")
print(f"E today: {inverter.e_today}")
print(f"E total: {inverter.e_total}")
print(f"Line 1 Voltage: {inverter.l1_voltage}")
print(f"Line 1 Frequency: {inverter.l1_frequency}")
print(f"Total running hours: {inverter.running_hours}")
print(f"Temperature: {inverter.temperature}")
