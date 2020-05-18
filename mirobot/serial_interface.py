import os
import time

import serial.tools.list_ports as lp

from .serial_device import SerialDevice
from .exceptions import MirobotError, MirobotAlarm, MirobotReset, MirobotAmbiguousPort

os_is_nt = os.name == 'nt'
os_is_posix = os.name == 'posix'


class SerialInterface:
    """ A class for bridging the interface between `mirobot.base_mirobot.BaseMirobot` and `mirobot.serial_device.SerialDevice`"""
    def __init__(self, mirobot, portname=None, baudrate=None, stopbits=None, exclusive=True, debug=False, logger=None, autofindport=True):
        """ Initialization of `SerialInterface` class

        Parameters
        ----------
        mirobot : `mirobot.base_mirobot.BaseMirobot`
            Mirobot object that this instance is attached to.
        portname : str
             (Default value = None) The portname to attach to. If `None`, and the `autofindport` parameter is `True`, then this class will automatically try to find an open port. It will attach to the first one that is available.
        baudrate : int
             (Default value = None) Baud rate of the connection.
        stopbits : int
             (Default value = None) Stopbits of the connection.
        exclusive : bool
             (Default value = True) Whether to exclusively block the port for this instance. Is only a true toggle on Linux and OSx; Windows always exclusively blocks serial ports. Setting this variable to `False` on Windows will throw an error.
        debug : bool
             (Default value = False) Whether to show debug statements in logger.
        logger : logger.Logger
             (Default value = None) Logger instance to use for this class. Usually `mirobot.base_mirobot.BaseMirobot.logger`.
        autofindport : bool
             (Default value = True) Whether to automatically search for an available port if `address` parameter is `None`.

        Returns
        -------

        """

        self.mirobot = mirobot

        if logger is not None:
            self.logger = logger

        self._debug = debug
        serial_device_kwargs = {'debug': debug, 'exclusive': exclusive}

        # check if baudrate was passed in args or kwargs, if not use the default value instead
        if baudrate is None:
            serial_device_kwargs['baudrate'] = 115200
        # check if stopbits was passed in args or kwargs, if not use the default value instead
        if stopbits is None:
            serial_device_kwargs['stopbits'] = 1

        # if portname was not passed in and autofindport is set to true, autosearch for a serial port
        if autofindport and portname is None:
            self.default_portname = self._find_portname()
            """ The default portname to use when making connections. To override this on a individual basis, provide portname to each invokation of `BaseMirobot.connect`. """
            serial_device_kwargs['portname'] = self.default_portname

        else:
            self.default_portname = portname

        self.serial_device = SerialDevice(**serial_device_kwargs)

    @property
    def debug(self):
        """ Return the `debug` property of `SerialInterface` """
        return self._debug

    @debug.setter
    def debug(self, value):
        """
        Set the new value for the `debug` property of `mirobot.serial_interface.SerialInterface`. Use as in `BaseMirobot.setDebug(value)`.
        Use this setter method as it will also update the logging objects of `mirobot.serial_interface.SerialInterface` and its `mirobot.serial_device.SerialDevice`. As opposed to setting `mirobot.serial_interface.SerialInterface._debug` directly which will not update the loggers.

        Parameters
        ----------
        value : bool
            The new value for `mirobot.serial_interface.SerialInterface._debug`.

        """
        self._debug = bool(value)
        self.serial_device.setDebug(value)

    def send(self, msg, disable_debug=False, wait=True, wait_idle=True):

        output = self.serial_device.send(msg)

        if self._debug and not disable_debug:
            self.logger.debug(f"[SENT] {msg}")

        if wait:
            output = self.wait_for_ok(disable_debug=disable_debug)

            if wait_idle:
                self.wait_until_idle()

        return output

    @property
    def is_connected(self):
        """
        Check if Mirobot is connected.

        Returns
        -------
        connected : bool
            Whether the Mirobot is connected.
        """
        return self.serial_device.is_open

    def _find_portname(self):
        """
        Find the port that might potentially be connected to the Mirobot.

        Returns
        -------
        device_name : str
            The name of the device that is (most-likely) connected to the Mirobot.
        """
        port_objects = lp.comports()

        if not port_objects:
            self.logger.exception(MirobotAmbiguousPort("No ports found! Make sure your Mirobot is connected and recognized by your operating system."))

        else:
            for p in port_objects:
                if os_is_posix:
                    try:
                        open(p.device)
                    except Exception:
                        continue
                    else:
                        return p.device
                else:
                    return p.device

            self.logger.exception(MirobotAmbiguousPort("No open ports found! Make sure your Mirobot is connected and is not being used by another process."))

    def wait_for_ok(self, reset_expected=False, disable_debug=False):
        """
        Continuously loops over and collects message output from the serial device.
        It stops when it encounters an 'ok' or otherwise terminal condition phrase.

        Parameters
        ----------
        reset_expected : bool
            (Default value = `False`) Whether a reset string is expected in the output (Example: on starting up Mirobot, output ends with a `'Using reset pos!'` rather than the traditional `'Ok'`)
        disable_debug : bool
            (Default value = `False`) Whether to override the class debug setting. Otherwise one will see status message debug output every 0.1 seconds, thereby cluttering standard output. Used primarily by `BaseMirobot.wait_until_idle`.

        Returns
        -------
        output : List[str]
            A list of output strings upto and including the terminal string.
        """
        output = ['']

        ok_eols = ['ok']

        reset_strings = ['Using reset pos!']

        def matches_eol_strings(terms, s):
            for eol in terms:
                if s.endswith(eol):
                    return True
            return False

        if reset_expected:
            eols = ok_eols + reset_strings
        else:
            eols = ok_eols

        if os_is_nt and not reset_expected:
            eol_threshold = 2
        else:
            eol_threshold = 1

        eol_counter = 0
        while eol_counter < eol_threshold:
            msg = self.serial_device.listen_to_device()

            if self._debug and not disable_debug:
                self.logger.debug(f"[RECV] {msg}")

            if 'error' in msg:
                self.logger.error(MirobotError(msg.replace('error: ', '')))

            if 'ALARM' in msg:
                self.logger.error(MirobotAlarm(msg.split('ALARM: ', 1)[1]))

            output.append(msg)

            if not reset_expected and matches_eol_strings(reset_strings, msg):
                self.logger.error(MirobotReset('Mirobot was unexpectedly reset!'))

            if matches_eol_strings(eols, output[-1]):
                eol_counter += 1

        return output[1:]  # don't include the dummy empty string at first index

    def wait_until_idle(self, refresh_rate=0.1):
        """
        Continuously loops over and refreshes state of the Mirobot.
        It stops when it encounters an 'Idle' state string.

        Parameters
        ----------
        refresh_rate : float
            (Default value = `0.1`) The rate in seconds to check for the 'Idle' state. Choosing a low number might overwhelm the controller on Mirobot. Be cautious when lowering this parameter.

        Returns
        -------
        output : List[str]
            A list of output strings upto and including the terminal string.
        """
        self.mirobot.update_status(disable_debug=True)

        while self.mirobot.status.state != 'Idle':
            time.sleep(refresh_rate)
            self.mirobot.update_status(disable_debug=True)

    def connect(self, portname=None):
        """
        Connect to the Mirobot.

        Parameters
        ----------
        portname : str
            (Default value = `None`) The name of the port to connnect to. If this is `None`, then it will try to use `self.default_portname`. If both are `None`, then an error will be thrown. To avoid this, specify a portname.

        Returns
        -------
        ok_msg : List[str]
            The output from an initial Mirobot connection.
        """
        if portname is None:
            if self.default_portname is not None:
                portname = self.default_portname
            else:
                self.logger.exception(ValueError('Portname must be provided! Example: `portname="COM3"`'))

        self.serial_device.portname = portname

        self.serial_device.open()

        return self.wait_for_ok(reset_expected=True)

    def disconnect(self):
        """ Disconnect from the Mirobot. Close the serial device connection. """
        if getattr(self, 'serial_device', None) is not None:
            self.serial_device.close()
