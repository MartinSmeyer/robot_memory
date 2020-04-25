from collections import namedtuple

from .base_mirobot import BaseMirobot
from .mirobot_status import MirobotAngles, MirobotCartesians

cartesian_function_splitter = namedtuple('cartesian_function_splitter', ['ptp', 'lin'])
coordinate_splitter = namedtuple('coordinate_splitter', ['cartesian', 'angle'])


class Mirobot(BaseMirobot):
    """ A class for managing and maintaining known Mirobot operations."""

    def __init__(self, *base_mirobot_args, **base_mirobot_kwargs):
        """
        Initialization of the `Mirobot` class.

        Parameters
        ----------
        *base_mirobot_args : Any
            Arguments that are passed into `mirobot.base_mirobot.BaseMirobot`. See `mirobot.base_mirobot.BaseMirobot.__init__` for more details.

        **base_mirobot_kwargs : Any
            Keyword arguments that are passed into `mirobot.base_mirobot.BaseMirobot`. See `mirobot.base_mirobot.BaseMirobot.__init__` for more details.

        Returns
        -------
        class : `Mirobot`

        """
        super().__init__(*base_mirobot_args, **base_mirobot_kwargs)

        self.move = coordinate_splitter(cartesian_function_splitter(self.go_to_cartesian_ptp, self.go_to_cartesian_ptp), self.go_to_axis)

        self.increment = coordinate_splitter(cartesian_function_splitter(self.increment_cartesian_ptp, self.increment_cartesian_lin), self.increment_axis)

    @property
    def state(self):
        """ The brief descriptor string for Mirobot's state. """
        return self.status.state

    @property
    def cartesian(self):
        """ Dataclass that holds the cartesian values and roll/pitch/yaw angles. """
        return self.status.cartesian

    @property
    def angle(self):
        """ Dataclass that holds Mirobot's angular values including the rail position value. """
        return self.status.angle

    @property
    def rail(self):
        """ Location of external slide rail module """
        return self.status.angle.d

    @property
    def valve_pwm(self):
        """ The current pwm of the value module. (eg. gripper) """
        return self.status.valve_pwm

    @property
    def pump_pwm(self):
        """ The current pwm of the pnuematic pump module. """
        return self.status.pump_pwm

    @property
    def motion_mode(self):
        """ Whether Mirobot is currently in coordinate mode (`False`) or joint-motion mode (`True`) """
        return self.status.motion_mode

    def go_to_zero(self, speed=None, wait=None):
        """
        Send all axes to their respective zero positions.

        Parameters
        ----------
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
        return self.go_to_axis(0, 0, 0, 0, 0, 0, 0, speed=speed, wait=wait)

    def go_to_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Linear move to a position in cartesian coordinates. (Command: `M20 G90 G1`)

        Parameters
        ----------
        x : Union[float, MirobotCartesians]
            (Default value = `None`) If `float`, this represents the X-axis position.
                                     If of type `mirobot.mirobot_status.MirobotCartesisans`, then this will be used for all positional values instead.
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
        if isinstance(x, MirobotCartesians):
            inputs = x.asdict()

        else:
            inputs = {'x': x, 'y': y, 'z': z, 'a': a, 'b': b, 'c': c}

        return super().go_to_cartesian_lin(**inputs,
                                           speed=speed, wait=wait)

    def go_to_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Point-to-point move to a position in cartesian coordinates. (Command: `M20 G90 G1`)

        Parameters
        ----------
        x : Union[float, MirobotCartesians]
            (Default value = `None`) If `float`, this represents the X-axis position.
                                     If of type `mirobot.mirobot_status.MirobotCartesisans`, then this will be used for all positional values instead.
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

        if isinstance(x, MirobotCartesians):
            inputs = x.asdict()

        else:
            inputs = {'x': x, 'y': y, 'z': z, 'a': a, 'b': b, 'c': c}

        return super().go_to_cartesian_ptp(**inputs,
                                           speed=speed, wait=wait)

    def go_to_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, d=None, speed=None, wait=None):
        """
        Send all axes to a specific position in angular coordinates. (Command: `M21 G90`)

        Parameters
        ----------
        x : Union[float, MirobotAngles]
            (Default value = `None`) If `float`, this represents the angle of axis 1.
                                     If of type `mirobot.mirobot_status.MirobotAngles`, then this will be used for all positional values instead.
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
        if isinstance(x, MirobotAngles):
            inputs = x.asdict()

        else:
            inputs = {'x': x, 'y': y, 'z': z, 'a': a, 'b': b, 'c': c, 'd': d}

        return super().go_to_axis(**inputs,
                                  speed=speed, wait=wait)

    def increment_cartesian_lin(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Linear increment in cartesian coordinates.

        Parameters
        ----------
        x : Union[float, MirobotCartesians]
            (Default value = `None`) If `float`, this represents the X-axis position.
                                     If of type `mirobot.mirobot_status.MirobotCartesisans`, then this will be used for all positional values instead.
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
        if isinstance(x, MirobotCartesians):
            inputs = x.asdict()

        else:
            inputs = {'x': x, 'y': y, 'z': z, 'a': a, 'b': b, 'c': c}

        return super().increment_cartesian_lin(**inputs,
                                               speed=speed, wait=wait)

    def increment_cartesian_ptp(self, x=None, y=None, z=None, a=None, b=None, c=None, speed=None, wait=None):
        """
        Point-to-point increment in cartesian coordinates. (Command: `M20 G91 G0`)

        Parameters
        ----------
        x : Union[float, MirobotCartesians]
            (Default value = `None`) If `float`, this represents the X-axis position.
                                     If of type `mirobot.mirobot_status.MirobotCartesisans`, then this will be used for all positional values instead.
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
        if isinstance(x, MirobotCartesians):
            inputs = x.asdict()

        else:
            inputs = {'x': x, 'y': y, 'z': z, 'a': a, 'b': b, 'c': c}

        return super().increment_cartesian_ptp(**inputs,
                                               speed=speed, wait=wait)

    def increment_axis(self, x=None, y=None, z=None, a=None, b=None, c=None, d=None, speed=None, wait=None):
        """
        Increment all axes a specified amount in angular coordinates. (Command: `M21 G91`)

        Parameters
        ----------
        x : Union[float, MirobotAngles]
            (Default value = `None`) If `float`, this represents the angle of axis 1.
                                     If of type `mirobot.mirobot_status.MirobotAngles`, then this will be used for all positional values instead.
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
        if isinstance(x, MirobotAngles):
            inputs = x.asdict()

        else:
            inputs = {'x': x, 'y': y, 'z': z, 'a': a, 'b': b, 'c': c, 'd': d}

        return super().increment_axis(**inputs,
                                      speed=speed, wait=wait)

    def increment_slide_rail(self, d, speed=None, wait=None):
        """ TODO: check that the commands in docstrings are right
        Increment slide rail position a specified amount. (Command: `M21 G91`)

        Parameters
        ----------
        d : float
            Location of slide rail module.
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

        return super().increment_axis(d=d,
                                      speed=speed, wait=wait)
