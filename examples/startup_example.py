#!/usr/bin/env python3
from mirobot import Mirobot


with Mirobot(portname='COM3', debug=True) as m:
    m.home_individual()

    m.go_to_zero()
