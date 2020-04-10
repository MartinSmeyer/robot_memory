from dataclasses import dataclass

@dataclass
class MirobotAngleValues:
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    d: float = 0.0

@dataclass
class MirobotCartesianValues:
    x:  float = 0.0
    y:  float = 0.0
    z:  float = 0.0
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0

@dataclass
class MirobotStatus:
    state: str = ''
    angle: MirobotAngleValues = MirobotAngleValues()
    cartesian: MirobotCartesianValues = MirobotCartesianValues()
    pump_pwm: int = 0
    valve_pwm: int = 0
    motion_mode: bool = False
