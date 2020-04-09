import serial
import sys
import os


class SerialDevice:
    def __init__(self, portname='', baudrate=0, stopbits=1):
        self.portname = portname
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.timeout = None
        self.serialport = serial.Serial()
        self._is_open = False

    # close the serial port when the class is deleted
    def __del__(self):
        try:
            if self._is_open:
                self.serialport.close()
        except Exception as e:
            print(e)
            print("Destructor error closing COM port: ", sys.exc_info()[0])

    # check if the serial port is open
    @property
    def is_open(self):
        self._is_open = self.serialport.is_open
        return self._is_open

    # listen to the serial port and pass the message to the callback
    def listen_to_device(self):
        while self._is_open:
            try:
                msg = self.serialport.readline()
                if msg != b'':
                    msg = str(msg.strip(), 'utf-8')

                    return msg

            except Exception as e:
                print(e)
                print("Error reading port: ", sys.exc_info()[0])

    # open the serial port
    def open(self):
        if not self._is_open:
            # serialport = 'portname', baudrate, bytesize = 8, parity = 'N', stopbits = 1, timeout = None, xonxoff = 0, rtscts = 0)
            self.serialport.port = self.portname
            self.serialport.baudrate = self.baudrate
            self.serialport.stopbits = self.stopbits
            try:
                self.serialport.open()
                self._is_open = True
            except Exception as e:
                print("Error opening COM port: ", sys.exc_info()[0])
                raise e

    # close the serial port
    def close(self):
        if self._is_open:
            try:
                self._is_open = False
                self.serialport.close()
            except Exception as e:
                print(e)
                print("Close error closing COM port: ", sys.exc_info()[0])

    # send a message to the serial port
    def send(self, message, terminator=os.linesep):
        if self._is_open:
            try:
                if not message.endswith(terminator):
                    message += terminator
                self.serialport.write(message.encode('utf-8'))
            except Exception as e:
                print(e)
                print("Error sending message: ", sys.exc_info()[0])
            else:
                return True
        else:
            return False
