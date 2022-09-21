#!/usr/bin/env python3
from mirobot import Mirobot

with Mirobot() as m:
    m.home_simultaneous()
