import serial
import sys
import os


class SerialDevice:
    """ A class for establishing a connection to a serial device. """
    def __init__(self, portname='', baudrate=0, stopbits=1):
        """ Initialization of `SerialDevice` class

        Parameters
        ----------
        portname :
             (Default value = '') Name of the port to connect to. (Example: 'COM3' or '/dev/ttyUSB1')
        baudrate :
             (Default value = 0) Baud rate of the connection.
        stopbits :
             (Default value = 1) Stopbits of the connection.

        Returns
        -------
        class : SerialDevice

        """
        self.portname = portname
        self.baudrate = int(baudrate)
        self.stopbits = int(stopbits)
        self.timeout = None
        self.serialport = serial.Serial()
        self._is_open = False

    def __del__(self):
        """ Close the serial port when the class is deleted """
        try:
            if self._is_open:
                self.serialport.close()
        except Exception as e:
            print(e)
            print("Destructor error closing COM port: ", sys.exc_info()[0])

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
                print(e)
                print("Error reading port: ", sys.exc_info()[0])

    def open(self):
        """ Open the serial port. """
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

    def close(self):
        """ Close the serial port. """
        if self._is_open:
            try:
                self._is_open = False
                self.serialport.close()
            except Exception as e:
                print(e)
                print("Close error closing COM port: ", sys.exc_info()[0])

    def send(self, message, terminator=os.linesep):
        """ Send a message to the serial port.

        Parameters
        ----------
        message :

        terminator :
             (Default value = os.linesep)

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
                print(e)
                print("Error sending message: ", sys.exc_info()[0])
            else:
                return True
        else:
            return False
