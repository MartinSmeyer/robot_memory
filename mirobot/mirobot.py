from contextlib import AbstractContextManager
import functools
import re

import serial.tools.list_ports as lp

from .serial_device import SerialDevice
from .mirobot_status import MirobotStatus
from .exceptions import MirobotError, MirobotAlarm, MirobotReset, MirobotAmbiguousPort, MirobotStatusError


class Mirobot(AbstractContextManager):
    """ A class for managing and maintaing known mirobot operations. """

    def __init__(self, *serial_device_args, debug=False, autoconnect=True, autofindport=True, valve_pwm_values=('65', '40'), pump_pwm_values=('0', '1000'), default_speed=2000, **serial_device_kwargs):
        """
        Initialization of `Mirobot` class.

        Parameters
        ----------
        *serial_device_args : List[Any]
             Arguments that are passed into the `SerialDevice` class.
        debug : bool
             (Default value = `False`) Whether to print gcode input and output to STDOUT. Stored in `Mirobot.debug`.
        autoconnect : bool
             (Default value = `True`) Whether to automatically attempt a connection to the Mirobot at the end of class creation. If this is set to `True`, manually connecting with `mirobot.connect()` is unnecessary.
        autofindport : bool
             (Default value = `True`) Whether to automatically find the serial port that the mirobot is attached to. If this is `False`, you must specify `portname='<portname>'` in `*serial_device_args`.
        valve_pwm_values : indexible-collection[str or numeric]
             (Default value = `('65', '40')`) The 'on' and 'off' values for the valve in terms of PWM. Useful if your mirobot is not calibrated correctly and requires different values to open and close. `Mirobot.set_valve` will only accept booleans and the values in this parameter, so if you have additional values you'd like to use, pass them in as additional elements in this tuple. Stored in `Mirobot.valve_pwm_values`.
        pump_pwm_values : indexible-collection[str or numeric]
             (Default value = `('0', '1000')`) The 'on' and 'off' values for the pnuematic pump in terms of PWM. Useful if your mirobot is not calibrated correctly and requires different values to open and close. `Mirobot.set_air_pump` will only accept booleans and the values in this parameter, so if you have additional values you'd like to use, pass them in as additional elements in this tuple. Stored in `Mirobot.pump_pwm_values`.
        default_speed : int
             (Default value = `2000`) This speed value will be passed in at each motion command, unless speed is specified as a function argument. Having this explicitly specified fixes phantom `Unknown Feed Rate` errors. Stored in `Mirobot.default_speed`.
        **serial_device_kwargs : Dict
             Keywords that are passed into the `SerialDevice` class.

        Returns
        -------
        class : Mirobot
        """

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
            """ The default portname to use when making connections. To override this on a individual basis, provide portname to each invokation of `Mirobot.connect`"""

        else:
            if 'portname' in args_dict:
                self.default_portname = args_dict['portname']
            elif 'portname' in serial_device_kwargs:
                self.default_portname = serial_device_kwargs['portname']
            else:
                self.default_portname = None

        self.serial_device = SerialDevice(*serial_device_args, **serial_device_kwargs)

        # see print statements of output
        self.debug = debug
        """ Boolean that determines if every input and output is be to printed to the screen. """

        self.valve_pwm_values = tuple(str(n) for n in valve_pwm_values)
        """ Collection of values to use for PWM values for valve module. First value is the 'On' position while the second is the 'Off' position. Only these values may be permitted. """
        self.pump_pwm_values = tuple(str(n) for n in pump_pwm_values)
        """ Collection of values to use for PWM values for pnuematic pump module. First value is the 'On' position while the second is the 'Off' position. Only these values may be permitted. """
        self.default_speed = default_speed
        """ The default speed to use when issuing commands that involve the speed parameter. """

        self.status = MirobotStatus()
        """ Dataclass that holds tracks mirobot's coordinates and pwm values among other quantities. See `mirobot.mirobot_status.MirobotStatus` for more details."""

        # do this at the very end, after everything is setup
        if autoconnect:
            self.connect()

    def __enter__(self):
        """ Magic method for contextManagers """
        return self

    def __exit__(self, *exc):
        """
        Magic method for contextManagers

        Parameters
        ----------
        *exc :


        Returns
        -------

        """
        self.disconnect()

    # COMMUNICATION #

    def wait_for_ok(self, reset_expected=False):
        """
        Continously loops over and collects message output from the serial device.
        It stops when it encounters and 'ok' or otherwise terminal condition phrase.

        Parameters
        ----------
        reset_expected : bool
             (Default value = `False`)

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

        while not matches_eol_strings(eols, output[-1]):
            msg = self.serial_device.listen_to_device()

            if self.debug:
                print(msg)

            if 'error' in msg:
                raise MirobotError(msg.replace('error: ', ''))
            if 'ALARM' in msg:
                raise MirobotAlarm(msg.split('ALARM: ')[1])

            output.append(msg)

            if not reset_expected and matches_eol_strings(reset_strings, msg):
                raise MirobotReset('Mirobot was unexpectedly reset!')
                break

        return output[1:]  # don't include the dummy empty string at first index

    def wait_for_ok_decorator(fn):
        """
        A decorator that will use the `wait` argument/keyword for a method to
        automatically use the `self.wait_for_ok` function call at the end of the
        wrapped function.

        Parameters
        ----------
        fn : func
             Function to wrap. Must have the `wait` argument or keyword.

        Returns
        -------
        wrapper : func
             A wrapper that decorates a function.
        """

        @functools.wraps(fn)
        def wait_for_ok_wrapper(self, *args, **kwargs):
            args_names = fn.__code__.co_varnames[:fn.__code__.co_argcount]
            args_dict = dict(zip(args_names, args))

            if 'wait' in args_dict:
                wait = args_dict.get('wait')
            elif 'wait' in kwargs:
                wait = kwargs.get('wait')
            else:
                wait = True

            output = fn(self, *args, **kwargs)

            if wait:
                return self.wait_for_ok()
            else:
                return output

        return wait_for_ok_wrapper

    # send a message
    @wait_for_ok_decorator
    def send_msg(self, msg, wait=True):
        """
        Send a message to the mirobot.

        Parameters
        ----------
        msg : str
             A message or instruction to send to the mirobot.
        wait : bool
             (Default value = `True`) Whether to wait for output to end and to return that output.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        if self.is_connected():
            output = self.serial_device.send(msg)
        if self.debug:
            print('Message sent: ', msg)

        if not wait:
            return output

    def get_status(self):
        """
        Get the status of the mirobot.

        Returns
        -------
        msg : List[str]
             The list of strings returned from a '?' status command.
        """
        instruction = '?'
        return self.send_msg(instruction)

    def update_status(self):
        """ Update the status of the mirobot. """
        status_msg = self.get_status()[0]
        new_status = self._parse_status(status_msg)
        self.status = new_status

    def _parse_status(self, msg):
        """
        Parse the status string of the mirobot and store the various values as class variables.

        Parameters
        ----------
        msg : str
             Status string that is obtained from a '?' instruction or `get_status` call.

        Returns
        -------
        return_status : MirobotStatus
             A new `MirobotStatus` object containing the new values obtained from `msg`.
        """

        return_status = MirobotStatus()

        state_regex = r'<([^,]*),Angle\(ABCDXYZ\):([-\.\d,]*),Cartesian coordinate\(XYZ RxRyRz\):([-.\d,]*),Pump PWM:(\d+),Valve PWM:(\d+),Motion_MODE:(\d)>'

        regex_match = re.fullmatch(state_regex, msg)

        if regex_match:
            try:
                state, angles, cartesians, pump_pwm, valve_pwm, motion_mode = regex_match.groups()
                self.status.state = state

                a, b, c, d, x, y, z = map(float, angles.split(','))

                return_status.angle.a = a
                return_status.angle.b = b
                return_status.angle.c = c
                return_status.angle.d = d
                return_status.angle.x = x
                return_status.angle.y = y
                return_status.angle.z = z

                x, y, z, a, b, c = map(float, cartesians.split(','))
                return_status.cartesian.x = x
                return_status.cartesian.y = y
                return_status.cartesian.z = z
                return_status.cartesian.a = a
                return_status.cartesian.b = b
                return_status.cartesian.c = c

                return_status.pump_pwm = int(pump_pwm)

                return_status.valve_pwm = int(valve_pwm)

                return_status.motion_mode = bool(motion_mode)

            except Exception as exception:
                raise Exception([MirobotStatusError(f'Could not parse status message "{msg}"'),
                                 exception])
            else:
                return return_status
        else:
            raise MirobotStatusError(f'Could not parse status message "{msg}"')

    def is_connected(self):
        """
        Check if mirobot is connected.

        Returns
        -------
        connected : bool
             Whether the mirobot is connected.
        """
        return self.serial_device.is_open

    def _find_portname(self):
        """
        Find the port that might potentially be connected to the mirobot.

        Returns
        -------
        device_name : str
             The name of the device that is (most-likely) connected to the mirobot.
        """
        port_objects = lp.comports()

        if not port_objects:
            raise MirobotAmbiguousPort("No ports found! Make sure your Mirobot is connected and recognized by your operating system.")

        if len(port_objects) > 1:
            raise MirobotAmbiguousPort(f"Unable to determine which port to automatically connect to!\nFound these ports: {[p.device for p in port_objects]}.\nTo fix this, please provide port name explicitly.")
        return port_objects[0].device

    def connect(self, portname=None):
        """
        Connect to the mirobot.

        Parameters
        ----------
        portname : str
             (Default value = `None`) The name of the port to connnect to. If this is `None`, then it will try to use `self.default_portname`. If both are `None`, then an error will be thrown. To avoid this, specify a portname.

        Returns
        -------
        ok_msg : List[str]
             The output from an initial mirobot connection.
        """
        if portname is None:
            if self.default_portname is not None:
                portname = self.default_portname
            else:
                raise ValueError('Portname must be provided! like so `portname=\'COM3\'`')

        self.serial_device.portname = portname

        self.serial_device.open()

        return self.wait_for_ok(reset_expected=True)

    def disconnect(self):
        """ Disconnect from the mirobot. Close the serial device connection. """
        self.serial_device.close()

    # COMMANDS #

    def home_individual(self, wait=True):
        """
        Home each axis individually. (Command: `$HH`)

        Parameters
        ----------
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = '$HH'
        return self.send_msg(msg, wait=wait)

    def home_simultaneous(self, wait=True):
        """
        Home all axes simultaneously. (Command:`$H`)

        Parameters
        ----------
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = '$H'
        return self.send_msg(msg, wait=wait)

    #
    def set_hard_limit(self, state, wait=True):
        """
        Set the hard limit state.

        Parameters
        ----------
        state : bool
             Whether to use the hard limit (`True`) or not (`False`).
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = f'$21={int(state)}'
        return self.send_msg(msg, wait=wait)

    # set the soft limit state
    def set_soft_limit(self, state, wait=True):
        """
        Set the soft limit state.

        Parameters
        ----------
        state : bool
             Whether to use the soft limit (`True`) or not (`False`).
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = f'$20={int(state)}'
        return self.send_msg(msg, wait=wait)

    def unlock_shaft(self, wait=True):
        """
        Unlock each axis on the mirobot. Homing naturally removes the lock. (Command:  "M50")

        Parameters
        ----------
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        msg = 'M50'
        return self.send_msg(msg, wait=wait)

    def go_to_zero(self, wait=True):
        """
        Send all axes to their respective zero positions.

        Parameters
        ----------
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        return self.go_to_axis(0, 0, 0, 0, 0, 0, 2000, wait=wait)

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

    def go_to_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        """
        Send all axes to a specific position in angular coordinates. (Command: `M21 G90`)

        Parameters
        ----------
        x : float{}
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
        speed : int
             (Default value = `None`) The speed in which the mirobot moves during this operation. (mm/s)
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

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

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    def increment_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
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
        speed : int
             (Default value = `None`) The speed in which the mirobot moves during this operation. (mm/s)
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

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

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self._generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    def go_to_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        """
        Point-to-point move to a position in cartesian coordinates. (Command: `M20 G90 G0`)

        Parameters
        ----------
        x :  float
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
             (Default value = `None`) The speed in which the mirobot moves during this operation. (mm/s)
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

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

        return self.send_msg(msg, wait=wait)

    def go_to_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
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
             (Default value = `None`) The speed in which the mirobot moves during this operation. (mm/s)
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

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

        return self.send_msg(msg, wait=wait)

    def increment_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
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
             (Default value = `None`) The speed in which the mirobot moves during this operation. (mm/s)
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

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

        return self.send_msg(msg, wait=wait)

    def increment_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        """
        Linear increment in cartesian coordinates.

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
             (Default value = `None`) The speed in which the mirobot moves during this operation. (mm/s)
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

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

        return self.send_msg(msg, wait=wait)

    # set the pwm of the air pump
    def set_air_pump(self, pwm, wait=True):
        """
        Sets the PWM of the pnuematic pump module.

        Parameters
        ----------
        pwm : int
             The pulse width modulation frequency to use.
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """

        if isinstance(pwm, bool):
            pwm = self.pump_pwm_values[not pwm]

        if str(pwm) not in self.pump_pwm_values:
            raise ValueError(f'pwm must be one of these values: {self.pump_pwm_values}. Was given {pwm}.')

        msg = f'M3S{pwm}'
        return self.send_msg(msg, wait=wait)

    def set_valve(self, pwm, wait=True):
        """
        Sets the PWM of the valve module.

        Parameters
        ----------
        pwm : int
             The pulse width modulation frequency to use.
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """

        if isinstance(pwm, bool):
            pwm = self.valve_pwm_values[not pwm]

        if str(pwm) not in self.valve_pwm_values:
            raise ValueError(f'pwm must be one of these values: {self.valve_pwm_values}. Was given {pwm}.')

        msg = f'M4E{pwm}'
        return self.send_msg(msg, wait=wait)

    def start_calibration(self, wait=True):
        """
        Starts the calibration sequence by setting all eeprom variables to zero. (Command: `M40`)

        Parameters
        ----------
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M40'
        return self.send_msg(instruction, wait=wait)

    def finish_calibration(self, wait=True):
        """
        Stop the calibration sequence and write results into eeprom variables. (Command: `M41`)

        Parameters
        ----------
        wait : bool
             (Default value = `True`) Whether to wait for output to return from the mirobot before returning from the function. This value determines if the function will block until the operation recieves feedback.

        Returns
        -------
        msg : List[str] or bool
             If `wait` is `True`, then return a list of strings which contains message output.
             If `wait` is `False`, then return whether sending the message succeeded.
        """
        instruction = 'M41'
        return self.send_msg(instruction, wait=wait)
