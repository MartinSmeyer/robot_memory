#!/usr/bin/env python3
from mirobot import Mirobot
import time
import math





def pick_card(m, x_robot, y_robot, z_robot=-20):
    res = m.go_to_cartesian_ptp(x_robot, y_robot, 0, 0,0,0)
    if 'ok' in res:
        m.set_air_pump(1000)
        res = m.go_to_cartesian_ptp(x_robot, y_robot, z_robot, 0,0,0)
        if not 'ok' in res:
            res = m.go_to_cartesian_ptp(math.copysign(1, x_robot) * (abs(x_robot)-10), 
                                        math.copysign(1, y_robot) * (abs(y_robot)-10), z_robot, 0,0,0)

        m.go_to_cartesian_ptp(x_robot, y_robot, 20)
        
        m.go_to_axis(x=40, y=-25, z=50, b=-205)
        # m.increment_axis(b=-185)
        return True
    else:
        return False
    
def place_card(m, x_robot, y_robot, z_robot=-20):
    m.increment_axis(b=185)
    m.go_to_cartesian_ptp(x_robot, y_robot, z_robot, 0,0,0)
    # m.go_to_cartesian_ptp(x_robot-25, y_robot, 0)
    m.set_air_pump(0)
    m.go_to_cartesian_ptp(x_robot, y_robot, 20)

    

if __name__ == "__main__":
        
    # MirobotCartesians(x=202.0, y=0.0, z=181.0, a=0.0, b=0.0, c=0.0)
    close_gripper = 'M3S1000M4E65'
    open_gripper = 'M3S0M4E40'

    # Default for `wait=` is `True`, but explicitly state it here to showcase this.
    with Mirobot(portname='/dev/ttyUSB0', wait=True, debug=True) as m:

        # Mirobot will by default wait for any command because we specified `wait=True` for the class above.
        m.home_simultaneous()
        
        # print our dataclass maintained by Mirobot. Shows the x,y,z,a,b,c coordinates.
        print(m.cartesian)

        # increment arm's position using a for-loop
        for count in range(1):
            mx = 202.00
            my = 0.00
            mz = 181

            print(f"************Count {count}************")

            # notice how we don't need any "wait" or "sleep" commands!
            # the following command will only return when the Mirobot returns 'Ok' and when Mirobot is 'Idle'
            m.go_to_cartesian_ptp(mx, my, mz)

            m.go_to_cartesian_ptp(mx, my, 0)
            m.set_air_pump(1000)
            m.go_to_cartesian_ptp(mx, my, -20)
            m.go_to_cartesian_ptp(mx, my, 80)
            m.increment_axis(b=-110)

            # turns here...
            m.go_to_cartesian_ptp(mx-25, my, -20)

            m.set_air_pump(0)
            m.go_to_cartesian_ptp(mx-25, my, mz)

            # m.go_to_cartesian_ptp(mx, -50, 180)
            # m.go_to_cartesian_ptp(mx, -50, count*19)
            # m.set_air_pump(0)
            # m.go_to_cartesian_ptp(mx, -50, 180)
            # m.go_to_cartesian_ptp(mx, my, 180)


            # print our cartesian coordinates again
            print(m.cartesian)
