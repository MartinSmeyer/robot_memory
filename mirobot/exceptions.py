import logging


class ExitOnExceptionStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        print(type(record))
        if record.levelno >= logging.ERROR:
            raise SystemExit(-1)


class MirobotError(Exception):
    """ An inplace class for throwing Mirobot errors. """
    pass


class MirobotAlarm(Exception):
    """  An inplace class for throwing Mirobot alarms. """
    pass


class MirobotReset(Exception):
    """ An inplace class for when Mirobot resets. """
    pass


class MirobotAmbiguousPort(Exception):
    """ An inplace class for when the serial port is unconfigurable. """
    pass


class MirobotStatusError(Exception):
    """ An inplace class for when Mirobot's status message is unprocessable. """
    pass


class MirobotResetFileError(Exception):
    """ An inplace class for when Mirobot has problems using the given reset file. """
    pass


class MirobotVariableCommandError(Exception):
    """ An inplace class for when Mirobot finds a command that does not match variable setting-command syntax. """
    pass


class SerialDeviceReadError(Exception):
    """ An inplace class for when SerialDevice is unable to read the serial port """


class SerialDeviceOpenError(Exception):
    """ An inplace class for when SerialDevice is unable to open the serial port """


class SerialDeviceLockError(Exception):
    """ An inplace class for when SerialDevice is unable to lock the serial port """


class SerialDeviceCloseError(Exception):
    """ An inplace class for when SerialDevice is unable to close the serial port """


class SerialDeviceUnlockError(Exception):
    """ An inplace class for when SerialDevice is unable to unlock the serial port """


class SerialDeviceWriteError(Exception):
    """ An inplace class for when SerialDevice is unable to write to the serial port """
