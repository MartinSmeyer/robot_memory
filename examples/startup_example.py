from time import sleep
from mirobot import Mirobot


with Mirobot(debug=True) as m:
    m.connect(portname='com3')

    sleep(3)

    m.home_simultaneous()

    sleep(10)
