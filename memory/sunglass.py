#!/usr/bin/env python3
from mirobot import Mirobot
import time

# MirobotCartesians(x=202.0, y=0.0, z=181.0, a=0.0, b=0.0, c=0.0)
close_gripper = 'M3S1000M4E65'
open_gripper = 'M3S0M4E40'

# Default for `wait=` is `True`, but explicitly state it here to showcase this.
with Mirobot(wait=True, debug=True) as m:

    # Mirobot will by default wait for any command because we specified `wait=True` for the class above.
    m.home_simultaneous()
    
    # print our dataclass maintained by Mirobot. Shows the x,y,z,a,b,c coordinates.
    print(m.cartesian)
    # m.go_to_cartesian_ptp(mx, my, mz)
    m.set_air_pump(1000)
    m.go_to_axis(0, 55, 0, 0, -155, 0)
    m.go_to_axis(0, 63, 0, 0, -155, 0)
    m.go_to_axis(0, 63, -3, 0, -155, 0)
    m.go_to_axis(0, 68, -5, 0, -155, 0)
    m.go_to_axis(0, 0, -45, 0, -60, 0)
    m.go_to_axis(0, 0, -45, 0, -60, 180)
    m.go_to_axis(-65, 0, -45, 0, -60, 180)

    m.set_air_pump(0)
