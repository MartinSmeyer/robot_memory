class MirobotError(Exception):
    pass


class MirobotAlarm(Warning):
    pass


class MirobotReset(Warning):
    pass


class MirobotAmbiguousPort(Exception):
    pass
