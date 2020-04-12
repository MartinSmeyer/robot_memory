class MirobotError(Exception):
    """ An inplace class for throwing mirobot errors. """
    pass


class MirobotAlarm(Warning):
    """  An inplace class for throwing mirobot alarms. """
    pass


class MirobotReset(Warning):
    """ An inplace class for when mirobot resets. """
    pass


class MirobotAmbiguousPort(Exception):
    """ An inplace class for when the serial port is unconfigurable. """
    pass


class MirobotStatusError(Exception):
    """ An inplace class for when mirobot's status message is unprocessable """
    pass
