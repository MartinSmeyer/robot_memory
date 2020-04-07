import sys
from contextlib import AbstractContextDecorator
from serial_device import SerialDevice


class Mirobot(AbstractContextDecorator):
    def __init__(self, receive_callback=None, debug=False):
        # The component to which this extension is attached
        self.serial_device = SerialDevice()
        self.receive_callback = receive_callback
        self.debug = debug

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.disconnect()

    # COMMUNICATION #

    # send a message
    def send_msg(self, msg):
        if self.is_connected():
            output = self.serial_device.send(msg)
        if self.debug:
            print('Message sent: ', msg)
        return output

    # message receive handler
    def _receive_msg(self, msg):
        msg = msg.decode('utf-8')
        if self.debug:
            print('Message received:', msg)
        if self.receive_callback is not None:
            try:
                self.receive_callback(msg)
            except Exception as e:
                print(e)
                print('Receive callback error: ', sys.exc_info()[0])

    # check if we are connected
    def is_connected(self):
        return self.serial_device.is_open

    # connect to the mirobot
    def connect(self, portname='COM3', receive_callback=None):
        self.serial_device.portname = portname
        self.serial_device.baudrate = 115200
        self.serial_device.stopbits = 1
        self.serial_device.listen_callback = self._receive_msg

        if receive_callback is not None:
            self.receive_callback = receive_callback

        self.serial_device.open()

    # set the receive callback
    def set_receive_callback(self, receive_callback):
        self.receive_callback = receive_callback

    # disconnect from the mirobot
    def disconnect(self):
        self.serial_device.close()

    # COMMANDS #

    # home each axis individually
    def home_individual(self):
        msg = '$HH'
        self.send_msg(msg)

    # home all axes simultaneously
    def home_simultaneous(self):
        msg = '$H'
        self.send_msg(msg)

    # set the hard limit state
    def set_hard_limit(self, state):
        msg = f'$21={int(state)}'
        self.send_msg(msg)

    # set the soft limit state
    def set_soft_limit(self, state):
        msg = f'$20={int(state)}'
        self.send_msg(msg)

    # unlock the shaft
    def unlock_shaft(self):
        msg = 'M50'
        self.send_msg(msg)

    # send all axes to their respective zero positions
    def go_to_zero(self):
        self.go_to_axis(0, 0, 0, 0, 0, 0, 2000)

    @staticmethod
    def generate_args_string(instruction, pairings):
        args = [f'{arg_key}{value}' for arg_key, value in pairings.items() if value is not None]

        return ' '.join([instruction] + args)

    # send all axes to a specific position
    def go_to_axis(self, a1=None, a2=None, a3=None, a4=None, a5=None, a6=None, speed=None):
        instruction = 'M21 G90'  # X{a1} Y{a2} Z{a3} A{a4} B{a5} C{a6} F{speed}
        if speed:
            speed = int(speed)

        pairings = {'X': a1, 'Y': a2, 'Z': a3, 'A': a4, 'B': a5, 'C': a6, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg)

    # increment all axes a specified amount
    def increment_axis(self, a1=None, a2=None, a3=None, a4=None, a5=None, a6=None, speed=None):
        instruction = 'M21 G91'  # X{a1} Y{a2} Z{a3} A{a4} B{a5} C{a6} F{speed}

        if speed:
            speed = int(speed)

        pairings = {'X': a1, 'Y': a2, 'Z': a3, 'A': a4, 'B': a5, 'C': a6, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg)

    # point to point move to a cartesian position
    def go_to_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None):
        instruction = 'M20 G90 G0'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg)

    # linear move to a cartesian position
    def go_to_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None):
        instruction = 'M20 G90 G1'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg)

    # point to point increment in cartesian space
    def increment_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None):
        instruction = 'M20 G91 G0'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg)

        self.send_msg(msg)
        return

    # linear increment in cartesian space
    def increment_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None):
        instruction = 'M20 G91 G1'  # X{x} Y{y} Z{z} A{a} B{b} C{c} F{speed}

        if speed:
            speed = int(speed)

        pairings = {'X': x, 'Y': y, 'Z': z, 'A': a, 'B': b, 'C': c, 'F': speed}
        msg = self.generate_args_string(instruction, pairings)

        return self.send_msg(msg)

    # set the pwm of the air pump
    def set_air_pump(self, pwm):
        valid_values = ('1000', '0')

        if isinstance(pwm, bool):
            pwm = valid_values[not pwm]

        if str(pwm) not in valid_values:
            raise ValueError(f'pwm must be one of these values: {valid_values}. Was given {pwm}.')

        msg = f'M3S{pwm}'
        self.send_msg(msg)

    # set the pwm of the gripper
    def set_gripper(self, pwm):
        valid_values = ('65', '40')

        if isinstance(pwm, bool):
            pwm = valid_values[not pwm]

        if str(pwm) not in valid_values:
            raise ValueError(f'pwm must be one of these values: {valid_values}. Was given {pwm}.')

        msg = f'M4E{pwm}'
        self.send_msg(msg)
