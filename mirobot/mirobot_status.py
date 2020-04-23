from dataclasses import dataclass


@dataclass
class MirobotAngles:
    """ A dataclass to hold Mirobot's angular values. """
    a: float = 0.0
    """ Angle of axis 1 """
    b: float = 0.0
    """ Angle of axis 2 """
    c: float = 0.0
    """ Angle of axis 3 """
    d: float = 0.0
    """ Location of external slide rail module """
    x: float = 0.0
    """ Angle of axis 4 """
    y: float = 0.0
    """ Angle of axis 5 """
    z: float = 0.0
    """ Angle of axis 6 """

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
class MirobotCartesians:
    """ A dataclass to hold Mirobot's cartesian values and roll/pitch/yaw angles. """
    x: float = 0.0
    """ Position on X-axis """
    y: float = 0.0
    """ Position of Y-axis """
    z: float = 0.0
    """ Position of Z-axis """
    a: float = 0.0
    """ Position of Roll angle """
    b: float = 0.0
    """ Position of Pitch angle """
    c: float = 0.0
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


@dataclass
class MirobotStatus:
    """ A composite dataclass to hold all of Mirobot's trackable quantities. """
    state: str = ''
    """ The brief descriptor string for Mirobot's state. """
    angle: MirobotAngles = MirobotAngles()
    """ Dataclass that holds Mirobot's angular values including the rail position value. """
    cartesian: MirobotCartesians = MirobotCartesians()
    """ Dataclass that holds the cartesian values and roll/pitch/yaw angles. """
    pump_pwm: int = 0
    """ The current pwm of the pnuematic pump module. """
    valve_pwm: int = 0
    """ The current pwm of the value module. (eg. gripper) """
    motion_mode: bool = False
    """ Whether Mirobot is currently in coordinate mode (`False`) or joint-motion mode (`True`) """
