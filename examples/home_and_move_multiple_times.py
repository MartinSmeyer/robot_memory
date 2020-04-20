from mirobot import Mirobot

# Default for `wait=` is `True`, but explicitly state it here to showcase this.
with Mirobot(wait=True) as m:

    # Mirobot will by default wait for any command because we specified `wait=True` above.
    m.home_simultaneous()

    # print our dataclass maintained by Mirobot. Shows the x,y,z,a,b,c coordinates.
    print(m.status.cartesian)

    # increment arm's position using a for-loop
    for count in range(5):
        mx = 180.00
        my = 0.00 + count * 5
        mz = 170 + count * 5

        print(f"************Count {count}**********")

        # notice how we don't need any "wait" or "sleep" commands!
        # the following command will only return when the Mirobot returns 'Ok' and when Mirobot is 'Idle'
        m.go_to_cartesian_ptp(mx, my, mz)

        print(m.status.cartesian)
