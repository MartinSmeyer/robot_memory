import portalocker
import serial
import sys
import os


class SerialDevice:
    """ A class for establishing a connection to a serial device. """
    def __init__(self, portname='', baudrate=0, stopbits=1, exclusive=True):
        """ Initialization of `SerialDevice` class

        Parameters
        ----------
        portname : str
             (Default value = `''`) Name of the port to connect to. (Example: 'COM3' or '/dev/ttyUSB1')
        baudrate : int
             (Default value = `0`) Baud rate of the connection.
        stopbits : int
             (Default value = `1`) Stopbits of the connection.
        exclusive : bool
             (Default value = `True`) Whether to (try) forcing exclusivity of serial ports. If another `mirobot.SerialDevice` is connected to this port, then don't connect at all. On the other hand, if no other `Mirobot.SerialDevice` is connected, then create a lock-file signaling that this serial port is in use.

        Returns
        -------
        class : SerialDevice

        """
        self.portname = str(portname)
        self.baudrate = int(baudrate)
        self.stopbits = int(stopbits)
        self.exclusive = exclusive

        self.serialport = serial.Serial()
        self._is_open = False

    def __del__(self):
        """ Close the serial port when the class is deleted """
        self.close()

    @property
    def is_open(self):
        """ Check if the serial port is open """
        self._is_open = self.serialport.is_open
        return self._is_open

    def listen_to_device(self):
        """ Listen to the serial port and return a message.

        Returns
        -------
        msg : str
            A single line that is read from the serial port.

        """
        while self._is_open:
            try:
                msg = self.serialport.readline()
                if msg != b'':
                    msg = str(msg.strip(), 'utf-8')

                    return msg

            except Exception as e:
                print("Error reading port: ", sys.exc_info()[0])
                raise e

    def open(self):
        """ Open the serial port. """
        if not self._is_open:
            # serialport = 'portname', baudrate, bytesize = 8, parity = 'N', stopbits = 1, timeout = None, xonxoff = 0, rtscts = 0)
            self.serialport.port = self.portname
            self.serialport.baudrate = self.baudrate
            self.serialport.stopbits = self.stopbits

            if self.exclusive:
                try:
                    portalocker.lock(self.serialport, portalocker.LOCK_EX | portalocker.LOCK_NB)
                except Exception:
                    raise Exception(f"Error locking serial port: Unable to acquire port {self.portname}. Make sure another process is not using it!")

            try:
                self.serialport.open()
                self._is_open = True
            except Exception as e:
                print("Error opening port: ", sys.exc_info()[0])
                raise e

    def close(self):
        """ Close the serial port. """
        if self._is_open:
            try:
                self._is_open = False
                self.serialport.close()
            except Exception as e:
                print("Error closing port: ", sys.exc_info()[0])
                raise e
            try:
                portalocker.unlock(self.serialport)
            except Exception as e:
                print("Error unlocking serial port: ", sys.exc_info()[0])
                raise e

    def send(self, message, terminator=os.linesep):
        """ Send a message to the serial port.

        Parameters
        ----------
        message : str
            The string to send to serial port.

        terminator : str
             (Default value = `os.linesep`) The line separator to use when signaling a new line. Usually `'\r\n'` for windows and `'\n'` for modern operating systems.

        Returns
        -------
        result : bool
            Whether the sending of `message` succeeded.

        """
        if self._is_open:
            try:
                if not message.endswith(terminator):
                    message += terminator
                self.serialport.write(message.encode('utf-8'))
            except Exception as e:
                print("Error sending message: ", sys.exc_info()[0])
                raise e
            else:
                return True
        else:
            return False
