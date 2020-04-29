from collections.abc import Collection
from contextlib import AbstractContextManager
import functools
import logging
import os
from pathlib import Path
import re
import time
from typing import TextIO, BinaryIO

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

import serial.tools.list_ports as lp

from .serial_device import SerialDevice
from .mirobot_status import MirobotStatus, MirobotAngles, MirobotCartesians
from .exceptions import ExitOnExceptionStreamHandler, MirobotError, MirobotAlarm, MirobotReset, MirobotAmbiguousPort, MirobotStatusError, MirobotResetFileError, MirobotVariableCommandError

os_is_nt = os.name == 'nt'
os_is_posix = os.name == 'posix'

if os_is_posix:
    import portalocker


class BaseMirobot(AbstractContextManager):
    """ A base class for managing and maintaining known Mirobot operations. """

    def __init__(self, *serial_device_args, debug=False, autoconnect=True, autofindport=True, valve_pwm_values=('65', '40'), pump_pwm_values=('0', '1000'), default_speed=2000, reset_file=None, wait=True, **serial_device_kwargs):
        """
        Initialization of the `BaseMirobot` class.

        Parameters
        ----------
        *serial_device_args : Any
             Arguments that are passed into the `mirobot.serial_device.SerialDevice` class.
        debug : bool
            (Default value = `False`) Whether to print gcode input and output to STDOUT. Stored in `BaseMirobot.debug`.
        autoconnect : bool
            (Default value = `True`) Whether to automatically attempt a connection to the Mirobot at the end of class creation. If this is `True`, manually connecting with `BaseMirobot.connect` is unnecessary.
        autofindport : bool
            (Default value = `True`) Whether to automatically find the serial port that the Mirobot is attached to. If this is `False`, you must specify `portname='<portname>'` in `*serial_device_args`.
        valve_pwm_values : indexible-collection[str or numeric]
            (Default value = `('65', '40')`) The 'on' and 'off' values for the valve in terms of PWM. Useful if your Mirobot is not calibrated correctly and requires different values to open and close. `BaseMirobot.set_valve` will only accept booleans and the values in this parameter, so if you have additional values you'd like to use, pass them in as additional elements in this tuple. Stored in `BaseMirobot.valve_pwm_values`.
        pump_pwm_values : indexible-collection[str or numeric]
            (Default value = `('0', '1000')`) The 'on' and 'off' values for the pnuematic pump in terms of PWM. Useful if your Mirobot is not calibrated correctly and requires different values to open and close. `BaseMirobot.set_air_pump` will only accept booleans and the values in this parameter, so if you have additional values you'd like to use, pass them in as additional elements in this tuple. Stored in `BaseMirobot.pump_pwm_values`.
        default_speed : int
            (Default value = `2000`) This speed value will be passed in at each motion command, unless speed is specified as a function argument. Having this explicitly specified fixes phantom `Unknown Feed Rate` errors. Stored in `BaseMirobot.default_speed`.
        reset_file : str or Path or Collection[str] or file-like
            (Default value = `None`) A file-like object, file-path, or str containing reset values for the Mirobot. The default (None) will use the commands in "reset.xml" provided by WLkata to reset the Mirobot. See `BaseMirobot.reset_configuration` for more details.
        wait : bool
            (Default value = `True`) Whether to wait for commands to return a status signifying execution has finished. Turns all move-commands into blocking function calls. Stored `BaseMirobot.wait`.
        **serial_device_kwargs : Any
             Keywords that are passed into the `mirobot.serial_device.SerialDevice` class.

        Returns
        -------
        class : `BaseMirobot`
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.stream_handler = ExitOnExceptionStreamHandler()
        self.stream_handler.setLevel(logging.DEBUG if debug else logging.INFO)

        formatter = logging.Formatter(f"[Mirobot Init] [%(levelname)s] %(message)s")
        self.stream_handler.setFormatter(formatter)
        self.logger.addHandler(self.stream_handler)

        # Parse inputs into SerialDevice
        serial_device_init_fn = SerialDevice.__init__
        args_names = serial_device_init_fn.__code__.co_varnames[:serial_device_init_fn.__code__.co_argcount]
        args_dict = dict(zip(args_names, serial_device_args))

        # check if baudrate was passed in args or kwargs, if not use the default value instead
        if not ('baudrate' in args_dict or 'baudrate' in serial_device_kwargs):
            serial_device_kwargs['baudrate'] = 115200
        # check if stopbits was passed in args or kwargs, if not use the default value instead
        if not ('stopbits' in args_dict or 'stopbits' in serial_device_kwargs):
            serial_device_kwargs['stopbits'] = 1

        # if portname was not passed in and autofindport is set to true, autosearch for a serial port
        if autofindport and not ('portname' in args_dict or 'portname' in serial_device_kwargs):
            self.default_portname = self._find_portname()
            """ The default portname to use when making connections. To override this on a individual basis, provide portname to each invokation of `BaseMirobot.connect`. """
            serial_device_kwargs['portname'] = self.default_portname

        else:
            if 'portname' in args_dict:
                self.default_portname = args_dict['portname']
            elif 'portname' in serial_device_kwargs:
                self.default_portname = serial_device_kwargs['portname']
            else:
                self.default_portname = None

        formatter = logging.Formatter(f"[{self.default_portname}] [%(levelname)s] %(message)s")
        self.stream_handler.setFormatter(formatter)
        # self.logger.addHandler(self.stream_handler)

        self.serial_device = SerialDevice(*serial_device_args, debug=debug, **serial_device_kwargs)

        self.reset_file = pkg_resources.read_text('mirobot.resources', 'reset.xml') if reset_file is None else reset_file
        """ The reset commands to use when resetting the Mirobot. See `BaseMirobot.reset_configuration` for usage and details. """
        self._debug = debug
        """ Boolean that determines if every input and output is to be printed to the screen. """

        self.valve_pwm_values = tuple(str(n) for n in valve_pwm_values)
        """ Collection of values to use for PWM values for valve module. First value is the 'On' position while the second is the 'Off' position. Only these values may be permitted. """
        self.pump_pwm_values = tuple(str(n) for n in pump_pwm_values)
        """ Collection of values to use for PWM values for pnuematic pump module. First value is the 'On' position while the second is the 'Off' position. Only these values may be permitted. """
        self.default_speed = default_speed
        """ The default speed to use when issuing commands that involve the speed parameter. """
        self.wait = wait
        """ Boolean that determines if every command should wait for a status message to return before unblocking function evaluation. Can be overridden on an individual basis by providing the `wait=` parameter to all command functions. """

        self.status = MirobotStatus()
        """ Dataclass that holds tracks Mirobot's coordinates and pwm values among other quantities. See `mirobot.mirobot_status.MirobotStatus` for more details."""

        # do this at the very end, after everything is setup
        if autoconnect:
            self.connect()

    def __enter__(self):
        """ Magic method for contextManagers """
        return self

    def __exit__(self, *exc):
        """ Magic method for contextManagers """
        self.disconnect()

    def __del__(self):
        """ Magic method for object deletion """
        self.disconnect()

    @property
    def debug(self):
        """ Return the `debug` property of `BaseMirobot` """
        return self._debug

    @debug.setter
    def debug(self, value):
        """
        Set the new value for the `debug` property of `mirobot.base_mirobot.BaseMirobot`. Use as in `BaseMirobot.setDebug(value)`.
        Use this setter method as it will also update the logging objects of `mirobot.base_mirobot.BaseMirobot` and its `mirobot.serial_device.SerialDevice`. As opposed to setting `mirobot.base_mirobot.BaseMirobot._debug` directly which will not update the loggers.

        Parameters
        ----------
        value : bool
            The new value for `mirobot.base_mirobot.BaseMirobot._debug`.

        """
        self._debug = bool(value)
        self.stream_handler.setLevel(logging.DEBUG if self._debug else logging.INFO)
        self.serial_device.setDebug(value)

    def wait_for_ok(self, reset_expected=False, disable_debug=False):
        """
        Continously loops over and collects message output from the serial device.
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

    def wait_decorator(fn):
        """
        A decorator that will use the `wait` argument for a method to automatically use the `BaseMirobot.wait_for_ok` and respectively, the `wait_idle` argument, for the `BaseMirobot.wait_until_idle` function calls at the end of the wrapped function.

        Parameters
        ----------
        fn : Callable
            Function to wrap. Must have the `wait` and or `wait_idle` argument or keyword.

        Returns
        -------
        wrapper : Callable
            A wrapper that decorates a function.
        """

        @functools.wraps(fn)
        def wait_wrapper(self, *args, **kwargs):
            args_names = fn.__code__.co_varnames[:fn.__code__.co_argcount]
            args_dict = dict(zip(args_names, args))

            def get_arg(arg_name, default=None):
                if arg_name in args_dict:
                    return args_dict.get(arg_name)
                elif arg_name in kwargs:
                    return kwargs.get(arg_name)
                else:
                    return default

            wait = get_arg('wait')
            disable_debug = get_arg('disable_debug')
            wait_idle = get_arg('wait_idle')

            output = fn(self, *args, **kwargs)

            if wait or (wait is None and self.wait):
                output = self.wait_for_ok(disable_debug=disable_debug)

                if wait_idle:
                    self.wait_until_idle()

            return output

        return wait_wrapper

    @wait_decorator
    def send_msg(self, msg, var_command=False, disable_debug=False, wait=None, wait_idle=False):
        """
        Send a message to the Mirobot.

        Parameters
        ----------
        msg : str or bytes
             A message or instruction to send to the Mirobot.
        var_command : bool
            (Default value = `False`) Whether `msg` is a variable command (of form `$num=value`). Will throw an error if does not validate correctly.
        disable_debug : bool
            (Default value = `False`) Whether to override the class debug setting. Used primarily by `BaseMirobot.wait_until_idle`.
        wait : bool
            (Default value = `None`) Whether to wait for output to end and to return that output. If `None`, use class default `BaseMirobot.wait` instead.
        wait_idle : bool
            (Default value = `False`) Whether to wait for Mirobot to be idle before returning.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        if self.is_connected:
            # convert to str from bytes
            if isinstance(msg, bytes):
                msg = str(msg, 'utf-8')

            # remove any newlines
            msg = msg.strip()

            # check if this is supposed to be a variable command and fail if not
            if var_command and not re.fullmatch(r'\$\d+=[\d\.]+', msg):
                self.logger.exception(MirobotVariableCommandError("Message is not a variable command: " + msg))

            # actually send the message
            output = self.serial_device.send(msg)

        if self._debug and not disable_debug:
            self.logger.debug(f"[SENT] {msg}")

        return output

    def get_status(self, disable_debug=False):
        """
        Get the status of the Mirobot. (Command: `?`)

        Parameters
        ----------
        disable_debug : bool
            (Default value = `False`) Whether to override the class debug setting. Used primarily by `BaseMirobot.wait_until_idle`.

        Returns
        -------
        msg : List[str]
            The list of strings returned from a '?' status command.

        """
        instruction = '?'
        # we don't want to wait for idle when checking status-- this leads to unbroken recursion!!
        return self.send_msg(instruction, disable_debug=disable_debug, wait=True, wait_idle=False)

    def update_status(self, disable_debug=False):
        """
        Update the status of the Mirobot.

        Parameters
        ----------
        disable_debug : bool
            (Default value = `False`) Whether to override the class debug setting. Used primarily by `BaseMirobot.wait_until_idle`.

        """
        # get only the status message and not 'ok'
        status_msg = self.get_status(disable_debug=disable_debug)[0]
        self.status = self._parse_status(status_msg)

    def _parse_status(self, msg):
        """
        Parse the status string of the Mirobot and store the various values as class variables.

        Parameters
        ----------
        msg : str
            Status string that is obtained from a '?' instruction or `BaseMirobot.get_status` call.

        Returns
        -------
        return_status : MirobotStatus
            A new `mirobot.mirobot_status.MirobotStatus` object containing the new values obtained from `msg`.
        """

        return_status = MirobotStatus()

        state_regex = r'<([^,]*),Angle\(ABCDXYZ\):([-\.\d,]*),Cartesian coordinate\(XYZ RxRyRz\):([-.\d,]*),Pump PWM:(\d+),Valve PWM:(\d+),Motion_MODE:(\d)>'

        regex_match = re.fullmatch(state_regex, msg)

        if regex_match:
            try:
                state, angles, cartesians, pump_pwm, valve_pwm, motion_mode = regex_match.groups()

                return_angles = MirobotAngles(**dict(zip('xyzdabc', map(float, angles.split(',')))))

                return_cartesians = MirobotCartesians(*map(float, cartesians.split(',')))

                return_status = MirobotStatus(state,
                                              return_angles,
                                              return_cartesians,
                                              int(pump_pwm),
                                              int(valve_pwm),
                                              bool(motion_mode))

            except Exception as exception:
                self.logger.exception(MirobotStatusError(f"Could not parse status message \"{msg}\""),
                                      exc_info=exception)
            else:
                return return_status
        else:
            self.logger.error(MirobotStatusError(f"Could not parse status message \"{msg}\""))

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
        self.update_status(disable_debug=True)

        while self.status.state != 'Idle':
            time.sleep(refresh_rate)
            self.update_status(disable_debug=True)

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
                        pf = open(p.device)
                        portalocker.lock(pf, portalocker.LOCK_EX | portalocker.LOCK_NB)
                        portalocker.unlock(pf)
                    except portalocker.LockException:
                        continue
                    else:
                        return p.device
                else:
                    return p.device

            self.logger.exception(MirobotAmbiguousPort("No open ports found! Make sure your Mirobot is connected and is not being used by another process."))

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
        if hasattr(self, 'serial_device'):
            self.serial_device.close()

    def home_individual(self, wait=None):
        """
        Home each axis individually. (Command: `$HH`)

        Parameters
        ----------
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = '$HH'
        return self.send_msg(msg, wait=wait, wait_idle=True)

    def home_simultaneous(self, wait=None):
        """
        Home all axes simultaneously. (Command:`$H`)

        Parameters
        ----------
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = '$H'
        return self.send_msg(msg, wait=wait, wait_idle=True)

    def set_hard_limit(self, state, wait=None):
        """
        Set the hard limit state.

        Parameters
        ----------
        state : bool
            Whether to use the hard limit (`True`) or not (`False`).
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = f'$21={int(state)}'
        return self.send_msg(msg, var_command=True, wait=wait)

    # set the soft limit state
    def set_soft_limit(self, state, wait=None):
        """
        Set the soft limit state.

        Parameters
        ----------
        state : bool
            Whether to use the soft limit (`True`) or not (`False`).
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = f'$20={int(state)}'
        return self.send_msg(msg, var_command=True, wait=wait)

    def unlock_shaft(self, wait=None):
        """
        Unlock each axis on the Mirobot. Homing naturally removes the lock. (Command: `M50`)

        Parameters
        ----------
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = 'M50'
        return self.send_msg(msg, wait=wait)

    @staticmethod
    def _generate_args_string(instruction, pairings):
        """
        A helper methods to generate argument strings for the various movement instructions.

        Parameters
        ----------
        instruction : str
            The command to include at the beginning of the string.
        pairings : dict[str:Any]
            A dictionary containing the pairings of argument name to argument value.
            If a value is `None`, it and its argument name is not included in the result.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
message
            A string containing the base command followed by the correctly formatted arguments.
        """
        args = [f'{arg_key}{value}' for arg_key, value in pairings.items() if value is not None]

        return ' '.join([instruction] + args)

    def go_to_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, d=None, speed=None, wait=None):
        """
        Send all axes to a specific position in angular coordinates. (Command: `M21 G90`)

        Parameters
        ----------
        x : float
            (Default value = `None`) Angle of axis 1.
        y : float
            (Default value = `None`) Angle of axis 2.
        z : float
            (Default value = `None`) Angle of axis 3.
        a : float
            (Default value = `None`) Angle of axis 4.
        b : float
            (Default value = `None`) Angle of axis 5.
        c : float
            (Default value = `None`) Angle of axis 6.
        d : float
            (Default value = `None`) Location of slide rail module.
        speed : int
            (Default value = `None`) The speed in which the Mirobot moves during this operation. (mm/s)
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M21 G90'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}
        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'D': d, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait, wait_idle=True)

    def increment_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, d=None, speed=None, wait=None):
        """
        Increment all axes a specified amount in angular coordinates. (Command: `M21 G91`)

        Parameters
        ----------
        x : float
            (Default value = `None`) Angle of axis 1.
        y : float
            (Default value = `None`) Angle of axis 2.
        z : float
            (Default value = `None`) Angle of axis 3.
        a : float
            (Default value = `None`) Angle of axis 4.
        b : float
            (Default value = `None`) Angle of axis 5.
        c : float
            (Default value = `None`) Angle of axis 6.
        d : float
            (Default value = `None`) Location of slide rail module.
        speed : int
            (Default value = `None`) The speed in which the Mirobot moves during this operation. (mm/s)
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M21 G91'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'D': d, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait, wait_idle=True)

    def go_to_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Point-to-point move to a position in cartesian coordinates. (Command: `M20 G90 G0`)

        Parameters
        ----------
        x : float
            (Default value = `None`) X-axis position.
        y : float
            (Default value = `None`) Y-axis position.
        z : float
            (Default value = `None`) Z-axis position.
        a : float
            (Default value = `None`) Orientation angle: Roll angle
        b : float
            (Default value = `None`) Orientation angle: Pitch angle
        c : float
            (Default value = `None`) Orientation angle: Yaw angle
        speed : int
            (Default value = `None`) The speed in which the Mirobot moves during this operation. (mm/s)
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M20 G90 G0'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait, wait_idle=True)

    def go_to_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Linear move to a position in cartesian coordinates. (Command: `M20 G90 G1`)

        Parameters
        ----------
        x : float
            (Default value = `None`) X-axis position.
        y : float
            (Default value = `None`) Y-axis position.
        z : float
            (Default value = `None`) Z-axis position.
        a : float
            (Default value = `None`) Orientation angle: Roll angle
        b : float
            (Default value = `None`) Orientation angle: Pitch angle
        c : float
            (Default value = `None`) Orientation angle: Yaw angle
        speed : int
            (Default value = `None`) The speed in which the Mirobot moves during this operation. (mm/s)
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M20 G90 G1'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait, wait_idle=True)

    def increment_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Point-to-point increment in cartesian coordinates. (Command: `M20 G91 G0`)

        Parameters
        ----------
        x : float
            (Default value = `None`) X-axis position.
        y : float
            (Default value = `None`) Y-axis position.
        z : float
            (Default value = `None`) Z-axis position.
        a : float
            (Default value = `None`) Orientation angle: Roll angle
        b : float
            (Default value = `None`) Orientation angle: Pitch angle
        c : float
            (Default value = `None`) Orientation angle: Yaw angle
        speed : int
            (Default value = `None`) The speed in which the Mirobot moves during this operation. (mm/s)
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M20 G91 G0'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait, wait_idle=True)

    def increment_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Linear increment in cartesian coordinates. (Command: `M20 G91 G1`)

        Parameters
        ----------
        x : float
            (Default value = `None`) X-axis position
        y : float
            (Default value = `None`) Y-axis position
        z : float
            (Default value = `None`) Z-axis position.
        a : float
            (Default value = `None`) Orientation angle: Roll angle
        b : float
            (Default value = `None`) Orientation angle: Pitch angle
        c : float
            (Default value = `None`) Orientation angle: Yaw angle
        speed : int
            (Default value = `None`) The speed in which the Mirobot moves during this operation. (mm/s)
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M20 G91 G1'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait, wait_idle=True)

    # set the pwm of the air pump
    def set_air_pump(self, pwm, wait=None):
        """
        Sets the PWM of the pnuematic pump module.

        Parameters
        ----------
        pwm : int
            The pulse width modulation frequency to use.
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """

        if isinstance(pwm, bool):
            pwm = self.pump_pwm_values[not pwm]

        if str(pwm) not in self.pump_pwm_values:
            self.logger.exception(ValueError(f'pwm must be one of these values: {self.pump_pwm_values}. Was given {pwm}.'))

        msg = f'M3S{pwm}'
        return self.send_msg(msg, wait=wait, wait_idle=True)

    def set_valve(self, pwm, wait=None):
        """
        Sets the PWM of the valve module.

        Parameters
        ----------
        pwm : int
            The pulse width modulation frequency to use.
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
            If `wait` is `True`, then return a list of strings which contains message output.
            If `wait` is `False`, then return whether sending the message succeeded.
        """

        if isinstance(pwm, bool):
            pwm = self.valve_pwm_values[not pwm]

        if str(pwm) not in self.valve_pwm_values:
            self.logger.exception(ValueError(f'pwm must be one of these values: {self.valve_pwm_values}. Was given {pwm}.'))

        msg = f'M4E{pwm}'
        return self.send_msg(msg, wait=wait, wait_idle=True)

    def start_calibration(self, wait=None):
        """
        Starts the calibration sequence by setting all eeprom variables to zero. (Command: `M40`)

        Parameters
        ----------
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M40'
        return self.send_msg(instruction, wait=wait)

    def finish_calibration(self, wait=None):
        """
        Stop the calibration sequence and write results into eeprom variables. (Command: `M41`)

        Parameters
        ----------
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M41'
        return self.send_msg(instruction, wait=wait)

    def reset_configuration(self, reset_file=None, wait=None):
        """
        Reset the Mirobot by resetting all eeprom variables to their factory settings. If provided an explicit `reset_file` on invocation, it will execute reset commands given in by `reset_file` instead of `self.reset_file`.

        Parameters
        ----------
        reset_file : str or Path or Collection[str] or file-like
            (Default value = `True`) A file-like object, Collection, or string containing reset values for the Mirobot. If given a string with newlines, it will split on those newlines and pass those in as "variable reset commands". Passing in the default value (None) will use the commands in "reset.xml" provided by WLkata to reset the Mirobot. If passed in a string without newlines, `BaseMirobot.reset_configuration` will try to open the file specified by the string and read from it. A `Path` object will be processed similarly. With a Collection (list-like) object, `BaseMirobot.reset_configuration` will use each element as the message body for `BaseMirobot.send_msg`. One can also pass in file-like objects as well (like `open('path')`).
        wait : bool
            (Default value = `None`) Whether to wait for output to return from the Mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback. If `None`, use class default `BaseMirobot.wait` instead.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """

        output = {}

        def send_each_line(file_lines):
            nonlocal output
            for line in file_lines:
                output[line] = self.send_msg(line, var_command=True, wait=wait)

        reset_file = reset_file if reset_file else self.reset_file

        if isinstance(reset_file, str) and '\n' in reset_file or \
           isinstance(reset_file, bytes) and b'\n' in reset_file:
            # if we find that we have a string and it contains new lines,
            send_each_line(reset_file.splitlines())

        elif isinstance(reset_file, (str, Path)):
            if not os.path.exists(reset_file):
                self.logger.exception(MirobotResetFileError("Reset file not found or reachable: {reset_file}"))
            with open(reset_file, 'r') as f:
                send_each_line(f.readlines())

        elif isinstance(reset_file, Collection) and not isinstance(reset_file, str):
            send_each_line(reset_file)

        elif isinstance(reset_file, (TextIO, BinaryIO)):
            send_each_line(reset_file.readlines())

        else:
            self.logger.exception(MirobotResetFileError(f"Unable to handle reset file of type: {type(reset_file)}"))

        return output
