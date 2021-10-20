import serial
import time


PORT = "COM4"
TIMEOUT = 1
BUFF_SIZE = 1024  # max size of received msg

HEAD = 0xAA  # msgs head
AUTO_BR = 0x55  # auto baudrate

REGS = {
    "STATUS": 0x00,
    "HW": 0x0A,
    "SW": 0x0C,
    "SN": 0x0E,
    "DIST": 0x20,
}

STATUS = {
    0x00: "NO ERROR",
    0x01: "POWER INPUT TOO LOW, POWER VOLTAGE SHOULD BE >= 2.2V",
    0x02: "INTERNAL ERROR, DON'T CARE",
    0x03: "MODULE TEMPERATURE IS TOO LOW (<-20 C)",
    0x04: "MODULE TEMPERATURE IS TOO HIGH (>40 C)",
    0x05: "TARGET OUT OF RANGE",
    0x06: "INVALID MEASURE RESULT",
    0x07: "BACKGROUND LIGHT TOO STRONG",
    0x08: "LASER SIGNAL TOO WEAK",
    0x09: "LASER SIGNAL TOO STRONG",
    0x0A: "HARDWARE FAULT 1",
    0x0B: "HARDWARE FAULT 2",
    0x0C: "HARDWARE FAULT 3",
    0x0D: "HARDWARE FAULT 4",
    0x0E: "HARDWARE FAULT 5",
    0x0F: "LASER SIGNAL NOT STABLE",
    0x10: "HARDWARE FAULT 6",
    0x11: "HARDWARE FAULT 7",
    0x81: "INVALID FRAME",
}


class DistanceSensor:
    def __init__(self, port):
        self.ser = serial.Serial(port=port, timeout=TIMEOUT)
        self.ADD_W, self.ADD_R = self.init_sensor()  # write and read addresses
        self.print_info()

        self.CMD_READ_ONCE = self.make_frame(reg=REGS["DIST"], payload_count=1, payload=0)

    def read_once(self):
        resp = self.send_msg(self.CMD_READ_ONCE)
        return self.get_payload(resp, last_byte=-3)

    def read(self, reg):
        """
        :param reg: register address to read
        :return: reg value as int
        """
        frame = self.make_frame(add=self.ADD_R, reg=reg)
        resp = self.send_msg(frame)
        return self.get_payload(resp)

    def get_status(self):
        return STATUS[self.read(reg=REGS["STATUS"])]

    def get_info(self):
        info = {
            "STATUS": self.get_status(),
            "HW VERS": self.read(reg=REGS["HW"]),
            "SW VERS": self.read(reg=REGS["SW"]),
            "SER. NUM.": hex(self.read(reg=REGS["SN"])).upper()[2:]
        }
        return info

    def print_info(self):
        """
        print status, hardware version, software version, and serial number
        """
        info = self.get_info()
        for k, v in info.items():
            print(k, "\t:\t", v)

    def init_sensor(self):
        time.sleep(0.1)
        self.ser.setRTS(False)
        time.sleep(1)
        msg = bytearray([AUTO_BR])
        self.ser.write(msg)
        add = self.ser.read_until()
        add = int.from_bytes(add, byteorder="big")
        return add, add + 128  # write and read addresses

    def prepare(self, num):
        """
        :param num: msg value
        :return: number split into two numbers <=255
        """
        ans = [0, num]
        c = num - 255
        if c > 0:
            ans[0] = c
        return ans

    def make_frame(self, head=HEAD, add=0, reg=0, payload_count=None, payload=None):
        """
        :param head: frame head
        :param add: slave address with read/write bit as msb
        :param reg: register address
        :param payload_count:
        :param payload:
        :return: frame bytearray
        checksum is calculated by summing all bytes except the frame head. byte overflow ignored
        """
        args = locals()
        checksum = 0
        frame = bytearray()
        for arg, val in args.items():
            if arg == "self" or val is None:
                continue
            checksum += val if arg != "head" else 0
            if arg in ("head", "add"):
                frame.append(val)
            else:
                frame.extend(self.prepare(val))
        frame.append(checksum % 256)
        return frame

    def get_payload(self, resp, first_byte=6, last_byte=-1):
        """
        :param resp: msg in bytes
        :param first_byte: first byte of payload
        :param last_byte: last byte of payload
        :return: payload bytes as an int
        """
        resp = list(resp)
        return int.from_bytes(bytes(resp[first_byte:last_byte]), byteorder="big")

    def send_msg(self, msg):
        self.ser.write(msg)
        resp = self.ser.read(BUFF_SIZE)
        return resp

    def clean(self):
        self.ser.setRTS(True)
        self.ser.close()


if __name__ == "__main__":
    s = DistanceSensor(port=PORT)
