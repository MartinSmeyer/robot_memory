from .base_mirobot import BaseMirobot


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
        super(self, *base_mirobot_args, **base_mirobot_kwargs)

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
        return self.go_to_axis(0, 0, 0, 0, 0, 0, speed if speed is not None else self.default_speed, wait=wait)
