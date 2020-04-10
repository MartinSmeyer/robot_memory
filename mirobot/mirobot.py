from contextlib import AbstractContextManager
import functools
import serial.tools.list_ports as lp

from serial_device import SerialDevice
from exceptions import MirobotError, MirobotAlarm, MirobotReset, MirobotAmbiguousPort


class Mirobot(AbstractContextManager):
    def __init__(self, *serial_device_args, debug=False, autoconnect=True, autofindport=True, gripper_pwm_pair=('65', '40'), default_speed=2000, **serial_device_kwargs):
        # The component to which this extension is attached

        # Parse inputs into SerialDevice
        serial_device_init_fn = SerialDevice.__init__
        args_names = serial_device_init_fn.__code__.co_varnames[:serial_device_init_fn.__code__.co_argcount]
        args_dict = dict(zip(args_names, serial_device_args))

        if not ('baudrate' in args_dict or 'baudrate' in serial_device_kwargs):
            serial_device_kwargs['baudrate'] = 115200
        if not ('stopbits' in args_dict or 'stopbits' in serial_device_kwargs):
            serial_device_kwargs['stopbits'] = 1

        if autofindport and not ('portname' in args_dict or 'portname' in serial_device_kwargs):
            self.default_portname = self._find_portname()
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

        self.gripper_pwm_values = tuple(str(n) for n in gripper_pwm_pair)
        self.default_speed = self.default_speed

        # do this at the very end, after everything is setup
        if autoconnect:
            self.connect()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.disconnect()

    # COMMUNICATION #

    def wait_for_ok(self, reset_expected=False):
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
        if self.is_connected():
            output = self.serial_device.send(msg)
        if self.debug:
            print('Message sent: ', msg)

        return output

    def get_status(self):
        instruction = '?'
        return self.send_msg(instruction)

    def update_status(self):
        pass

    # check if we are connected
    def is_connected(self):
        return self.serial_device.is_open

    def _find_portname(self):
        port_objects = lp.comports()

        if not port_objects:
            raise MirobotAmbiguousPort("No ports found! Make sure your Mirobot is connected and recognized by your operating system.")

        if len(port_objects) > 1:
            raise MirobotAmbiguousPort(f"Unable to determine which port to automatically connect to!\nFound these ports: {[p.device for p in port_objects]}.\nTo fix this, please provide port name explicitly.")
        return port_objects[0].device

    # connect to the mirobot
    def connect(self, portname=None):
        if portname is None:
            if self.default_portname is not None:
                portname = self.default_portname
            else:
                raise ValueError('Portname must be provided! like so `portname=\'COM3\'`')

        self.serial_device.portname = portname

        self.serial_device.open()

        return self.wait_for_ok(reset_expected=True)

    # disconnect from the mirobot
    def disconnect(self):
        self.serial_device.close()

    # COMMANDS #

    # home each axis individually
    def home_individual(self, wait=True):
        msg = '$HH'
        return self.send_msg(msg, wait=wait)

    # home all axes simultaneously
    def home_simultaneous(self, wait=True):
        msg = '$H'
        return self.send_msg(msg, wait=wait)

    # set the hard limit state
    def set_hard_limit(self, state, wait=True):
        msg = f'$21={int(state)}'
        return self.send_msg(msg, wait=wait)

    # set the soft limit state
    def set_soft_limit(self, state, wait=True):
        msg = f'$20={int(state)}'
        return self.send_msg(msg, wait=wait)

    # unlock the shaft
    def unlock_shaft(self, wait=True):
        msg = 'M50'
        return self.send_msg(msg, wait=wait)

    # send all axes to their respective zero positions
    def go_to_zero(self, wait=True):
        return self.go_to_axis(0, 0, 0, 0, 0, 0, 2000, wait=wait)

    @staticmethod
    def generate_args_string(instruction, pairings):
        args = [f'{arg_key}{value}' for arg_key, value in pairings.items() if value is not None]

        return ' '.join([instruction] + args)

    # send all axes to a specific position
    def go_to_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        instruction = 'M21 G90'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}
        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    # increment all axes a specified amount
    def increment_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        instruction = 'M21 G91'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    # point to point move to a cartesian position
    def go_to_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        instruction = 'M20 G90 G0'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    # linear move to a cartesian position
    def go_to_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        instruction = 'M20 G90 G1'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    # point to point increment in cartesian space
    def increment_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        instruction = 'M20 G91 G0'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    # linear increment in cartesian space
    def increment_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=True):
        instruction = 'M20 G91 G1'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if not speed:
            speed = self.default_speed
        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg, wait=wait)

    # set the pwm of the air pump
    def set_air_pump(self, pwm, wait=True):
        valid_values = ('1000', '0')

        if isinstance(pwm, bool):
            pwm = valid_values[not pwm]

        if str(pwm) not in valid_values:
            raise ValueError(f'pwm must be one of these values: {valid_values}. Was given {pwm}.')

        msg = f'M3S{pwm}'
        return self.send_msg(msg, wait=wait)

    # set the pwm of the gripper
    def set_gripper(self, pwm, wait=True):
        valid_values = self.gripper_pwm_values

        if isinstance(pwm, bool):
            pwm = valid_values[not pwm]

        if str(pwm) not in valid_values:
            raise ValueError(f'pwm must be one of these values: {valid_values}. Was given {pwm}.')

        msg = f'M4E{pwm}'
        return self.send_msg(msg, wait=wait)

    def start_calibration(self, wait=True):
        instruction = 'M40'
        return self.send_msg(instruction, wait=wait)

    def finish_calibration(self, wait=True):
        instruction = 'M41'
        return self.send_msg(instruction, wait=wait)
