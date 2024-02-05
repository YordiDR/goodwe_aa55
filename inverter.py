from __future__ import annotations

from enum import Enum
import socket
from typing import Any

from .exceptions import InverterError, RequestFailedException


class InverterStatus(Enum):
    Offline = -1
    Waiting = 0
    Online = 1
    Error = 2


class Inverter:
    """Class representing Goodwe inverter"""

    # Properties
    host: str = None
    port: int = -1
    serial_number: str = None
    model: str = None
    work_mode: int = -1
    work_mode_string: str = None
    pac: int = -1
    e_today: float = -1
    e_total: float = -1
    l1_voltage: float = -1
    l1_frequency: float = -1
    temperature: float = -1
    running_hours: int = -1
    mock: bool = False

    # Constructor
    def __init__(self, host: str, port: int, mock: bool = False) -> None:
        if host is None:
            raise InverterError("No host to connect to was specified.")
        self.host = host

        if port is None:
            raise InverterError("No port to connect to was specified.")
        self.port = port

        self.mock = mock

        device_info = self._query_id_info()

        self.model = device_info["model"]
        self.serial_number = device_info["serial_number"]

    def _execute_aa55_command(self, message) -> bytes:
        # Calculate the expected response header
        expectedHeader = (
            message[0:2]
            + message[3:4]
            + message[2:3]
            + message[4:5]
            + (message[5] + 128).to_bytes()
        )
        response = b""

        # Send the message to the inverter
        cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cs.settimeout(1)
        cs.sendto(message, (self.host, self.port))

        # Check if the first received part of data contains the expected header
        try:
            curResponse = cs.recv(150)
        except TimeoutError as error:
            raise RequestFailedException(
                f'The inverter did not respond to the "{message.hex()}" command.'
            ) from error

        if len(curResponse) < 9:
            raise RequestFailedException(
                f'Invalid response received to the "{message.hex()}" command. At least nine bytes should be received (AA55 headers + CRC). Received: {curResponse.hex()}'
            )

        if curResponse[0:6] != expectedHeader:
            raise RequestFailedException(
                f"Received header does not match the expected header, received {curResponse[0:6].hex()} instead of {expectedHeader.hex()}"
            )

        # Header was successfully received (bytes 0-5), the next byte should be the length of the payload
        payloadLength = curResponse[6]

        # Full length of the response should be headers (7 bytes including payload length) + payload + CRC (2 bytes)
        expectedResponseLength = 7 + payloadLength + 2

        response += curResponse

        while len(response) != expectedResponseLength:
            try:
                curResponse = cs.recv(150)

            except TimeoutError as error:
                raise RequestFailedException(
                    f'The inverter stopped sending data while we are still expecting data for the "{message.hex()}" command. Received response: {curResponse.hex()}'
                ) from error

            response += curResponse

        print(f'Full response to command "{message.hex()}" received from inverter.')
        cs.close()
        payload = response[7:-2]

        # Check CRC
        receivedCRC = int(response[-2:].hex(), 16)
        calculatedCRC = 0
        bytesToCRC = response[0:-2]
        for byte in bytesToCRC:
            calculatedCRC += byte

        if calculatedCRC != receivedCRC:
            print(
                f'CRC error detected. Calculated CRC: {calculatedCRC}, received CRC {receivedCRC} for command "{message.hex()}"'
            )
            raise RequestFailedException(
                f'CRC error detected. Calculated CRC: {calculatedCRC}, received CRC {receivedCRC} for command "{message.hex()}"'
            )
        print("CRC validated successfully.")

        return payload

    def _query_id_info(self) -> dict[str, str]:
        # Execute query id info command
        if not self.mock:
            payload = self._execute_aa55_command(
                b"\xaa\x55\xc0\x7f\x01\x02\x00\x02\x41"
            )
        else:
            payload = bytes.fromhex(
                "20202020204757313530302d58532020202020202020202020202020202020353135303053535832313157303431332020202020202020202020202020202006"
            )

        # Parse response
        model = payload[5:15].decode("ascii").rstrip()
        serial_number = payload[31:47].decode("ascii").rstrip()

        return {"model": model, "serial_number": serial_number}

    def _query_running_info(self) -> dict[str, str]:
        # Execute query running info command
        if not self.mock:
            payload = self._execute_aa55_command(
                b"\xaa\x55\xc0\x7f\x01\x01\x00\x02\x40"
            )
        else:
            payload = bytes.fromhex(
                "06ae000000080000094d0005138c0089000100f10000000000007a9000001bfc141f0000019501400edd0006000018011e0a1d0500eb003d000e0000"
            )

        # Parse response
        l1_voltage = int(payload[8:10].hex(), 16) / 10
        l1_frequency = int(payload[12:14].hex(), 16) / 100
        pac = int(payload[14:16].hex(), 16)
        work_mode = int(payload[16:18].hex(), 16)
        temperature = int(payload[18:20].hex(), 16) / 10
        e_total = int(payload[24:28].hex(), 16) / 10
        running_hours = int(payload[30:32].hex(), 16)
        e_today = int(payload[44:46].hex(), 16) / 10

        return {
            "work_mode": work_mode,
            "pac": pac,
            "e_today": e_today,
            "e_total": e_total,
            "l1_voltage": l1_voltage,
            "l1_frequency": l1_frequency,
            "temperature": temperature,
            "running_hours": running_hours,
        }

    async def get_running_info(self) -> dict[str, Any]:
        """Retrieves the running information from the inverter and updates the inverter object."""

        try:
            device_runningInfo = self._query_running_info()
        except TimeoutError:
            print("Inverter is offline.")
            self.work_mode = -1
            self.work_mode_string = InverterStatus(self.work_mode).name
            self.pac = 0
            self.l1_voltage = 0
            self.l1_frequency = 0
            self.temperature = 0
            return
        except:
            print("An error occurred during the retrieval of the running info.")
            return

        self.work_mode = device_runningInfo["work_mode"]
        self.work_mode_string = InverterStatus(self.work_mode).name
        self.pac = device_runningInfo["pac"]
        self.e_today = device_runningInfo["e_today"]
        self.e_total = device_runningInfo["e_total"]
        self.l1_voltage = device_runningInfo["l1_voltage"]
        self.l1_frequency = device_runningInfo["l1_frequency"]
        self.temperature = device_runningInfo["temperature"]
        self.running_hours = device_runningInfo["running_hours"]

        return {
            "work_mode": self.work_mode_string,
            "pac": self.pac,
            "e_today": self.e_today,
            "e_total": self.e_total,
            "l1_voltage": self.l1_voltage,
            "l1_frequency": self.l1_frequency,
            "temperature": self.temperature,
        }
