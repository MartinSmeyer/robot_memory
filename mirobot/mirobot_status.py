from dataclasses import dataclass, asdict, astuple


class featured_dataclass:
    def asdict(self):
        return asdict(self)

    def astuple(self):
        return astuple(self)



@dataclass
class MirobotAngles(featured_dataclass):
    """ A dataclass to hold Mirobot's angular values. """
    a: float = 0.0
    """ Angle of axis 1 """
    b: float = 0.0
    """ Angle of axis 2 """
    c: float = 0.0
    """ Angle of axis 3 """
    x: float = 0.0
    """ Angle of axis 4 """
    y: float = 0.0
    """ Angle of axis 5 """
    z: float = 0.0
    """ Angle of axis 6 """
    d: float = 0.0
    """ Location of external slide rail module """

    @property
    def a1(self):
        """ Angle of axis 1 """
        return self.a

    @property
    def a2(self):
        """ Angle of axis 2 """
        return self.b

    @property
    def a3(self):
        """ Angle of axis 3 """
        return self.c

    @property
    def a4(self):
        """ Angle of axis 4 """
        return self.x

    @property
    def a5(self):
        """ Angle of axis 5 """
        return self.y

    @property
    def a6(self):
        """ Angle of axis 6 """
        return self.z

    @property
    def rail(self):
        """ Location of external slide rail module """
        return self.d


@dataclass
class MirobotCartesians(featured_dataclass):
    """ A dataclass to hold Mirobot's cartesian values and roll/pitch/yaw angles. """
    x: float = None
    """ Position on X-axis """
    y: float = None
    """ Position of Y-axis """
    z: float = None
    """ Position of Z-axis """
    a: float = None
    """ Position of Roll angle """
    b: float = None
    """ Position of Pitch angle """
    c: float = None
    """ Position of Yaw angle """

    @property
    def tx(self):
        """ Position on X-axis """
        return self.x

    @property
    def ty(self):
        """ Position on Y-axis """
        return self.y

    @property
    def tz(self):
        """ Position on Z-axis """
        return self.z

    @property
    def rx(self):
        """ Position of Roll angle """
        return self.a

    @property
    def ry(self):
        """ Position of Pitch angle """
        return self.b

    @property
    def rz(self):
        """ Position of Yaw angle """
        return self.c


class MirobotStatus(featured_dataclass):
@dataclass
    """ A composite dataclass to hold all of Mirobot's trackable quantities. """
    state: str = ''
    """ The brief descriptor string for Mirobot's state. """
    angle: MirobotAngles = MirobotAngles()
    """ Dataclass that holds Mirobot's angular values including the rail position value. """
    cartesian: MirobotCartesians = MirobotCartesians()
    """ Dataclass that holds the cartesian values and roll/pitch/yaw angles. """
    pump_pwm: int = None
    """ The current pwm of the pnuematic pump module. """
    valve_pwm: int = None
    """ The current pwm of the value module. (eg. gripper) """
    motion_mode: bool = False
    """ Whether Mirobot is currently in coordinate mode (`False`) or joint-motion mode (`True`) """
