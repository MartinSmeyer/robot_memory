from dataclasses import dataclass, asdict, astuple, fields
import numbers
import operator


class basic_dataclass:
    def asdict(self):
        return asdict(self)

    def astuple(self):
        return astuple(self)

    def fields(self):
        return fields(self)

    @classmethod
    def _new_from_dict(cls, dictionary):
        return cls(**dictionary)


class featured_dataclass(basic_dataclass):
    def _cross_same_type(self, other, operation_function, single=False):
        new_values = {}
        for f in self.fields():
            this_value = getattr(self, f.name)

            if single:
                other_value = other
            else:
                other_value = getattr(other, f.name)

            result = operation_function(this_value, other_value)

            new_values[f.name] = result

        return new_values

    def _binary_operation(self, other, operation):
        def operation_function(this_value, other_value):
            if None in (this_value, other_value):
                return None
            else:
                return operation(this_value, other_value)

        if isinstance(other, type(self)):
            new_values = self._cross_same_type(other, operation_function)

        elif isinstance(other, numbers.Real):
            new_values = self._cross_same_type(other, operation_function, single=True)

        else:
            raise NotImplementedError(f"Cannot handle {type(self)} and {type(other)}")

        return self._new_from_dict(new_values)

    def _unary_operation(self, operation_function):
        new_values = {f.name: operation_function(f)
                      for f in self.fields()}

        return self._new_from_dict(new_values)

    def _basic_unary_operation(self, operation):
        def operation_function(field):
            value = getattr(self, field.name)
            if value is not None:
                return operation(value)
            else:
                return None

        return self._unary_operation(operation_function)

    def _comparision_operation(self, other, operation):
        def operation_function(this_value, other_value):
            if None in (this_value, other_value):
                return True
            else:
                return operation(this_value, other_value)

        if isinstance(other, type(self)):
            new_values = self._cross_same_type(other, operation_function).values()

        elif isinstance(other, (int, float)):
            new_values = self._cross_same_type(other, operation_function, single=True).values()

        else:
            raise NotImplementedError(f"Cannot handle {type(self)} and {type(other)}")

        if all(new_values):
            return True

        elif not any(new_values):
            return False

        else:
            return None

    def __or__(self, other):
        def operation_function(this_value, other_value):
            if this_value is None:
                return other_value
            else:
                return this_value

        new_values = self._cross_same_type(other, operation_function)
        return self._new_from_dict(new_values)

    def __and__(self, other):
        def operation_function(this_value, other_value):
            if None not in (this_value, other_value):
                return this_value
            else:
                return None

        new_values = self._cross_same_type(other, operation_function)
        return self._new_from_dict(new_values)

    def int(self):
        def operation_function(field):
            value = getattr(self, field.name)
            if field.type in (float,) and value is not None:
                return int(value)
            else:
                return value

        return self._unary_operation(operation_function)

    def round(self):
        def operation_function(field):
            value = getattr(self, field.name)
            if field.type in (float,) and value is not None:
                return round(value)
            else:
                return value

        return self._unary_operation(operation_function)

    def __add__(self, other):
        return self._binary_operation(other, operator.add)

    def __radd__(self, other):
        return self._binary_operation(other, operator.add)

    def __sub__(self, other):
        return self._binary_operation(other, operator.sub)

    def __rsub__(self, other):
        def rsub(dataclass_value, number):
            return operator.sub(number, dataclass_value)

        return self._binary_operation(other, rsub)

    def __mul__(self, other):
        return self._binary_operation(other, operator.mul)

    def __rmul__(self, other):
        return self._binary_operation(other, operator.mul)

    def __div__(self, other):
        return self._binary_operation(other, operator.div)

    def __rdiv__(self, other):
        def rdiv(dataclass_value, number):
            return operator.div(number, dataclass_value)

        return self._binary_operation(other, rdiv)

    def __truediv__(self, other):
        return self._binary_operation(other, operator.truediv)

    def __rtruediv__(self, other):
        def rtruediv(dataclass_value, number):
            return operator.truediv(number, dataclass_value)

        return self._binary_operation(other, operator.truediv)

    def __mod__(self, other):
        return self._binary_operation(other, operator.mod)

    def __abs__(self):
        return self._basic_unary_operation(operator.abs)

    def __pos__(self):
        return self._basic_unary_operation(operator.pos)

    def __neg__(self):
        return self._basic_unary_operation(operator.neg)

    def __lt__(self, other):
        return self._comparision_operation(other, operator.lt)

    def __le__(self, other):
        return self._comparision_operation(other, operator.le)

    def __eq__(self, other):
        return self._comparision_operation(other, operator.eq)

    def __ne__(self, other):
        return self._comparision_operation(other, operator.ne)

    def __ge__(self, other):
        return self._comparision_operation(other, operator.ge)

    def __gt__(self, other):
        return self._comparision_operation(other, operator.gt)


@dataclass
class MirobotAngles(featured_dataclass):
    """ A dataclass to hold Mirobot's angular values. """
    a: float = None
    """ Angle of axis 1 """
    b: float = None
    """ Angle of axis 2 """
    c: float = None
    """ Angle of axis 3 """
    x: float = None
    """ Angle of axis 4 """
    y: float = None
    """ Angle of axis 5 """
    z: float = None
    """ Angle of axis 6 """
    d: float = None
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


@dataclass
class MirobotStatus:
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
