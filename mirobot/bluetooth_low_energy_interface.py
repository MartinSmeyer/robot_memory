import asyncio
import re
import time


from bleak import discover, BleakClient
# import nest_asyncio
# nest_asyncio.apply()


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class BluetoothLowEnergyInterface:
    def __init__(self, mirobot, address=None, debug=False, logger=None, autofindaddress=True):

        self.mirobot = mirobot

        if logger is not None:
            self.logger = logger

        self._debug = debug

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.run_and_get(self._init())

    async def _init(self, address=None, autofindaddress=True):
        # if portname was not passed in and autofindport is set to true, autosearch for a serial port
        if autofindaddress and address is None:
            self.default_portname = self.address = await self._find_address()
            """ The default portname to use when making connections. To override this on a individual basis, provide portname to each invocation of `BaseMirobot.connect`. """
        else:
            self.address = address

        self.client = BleakClient(self.address, loop=self.loop)

    def run_and_get(self, coro):
        # task = asyncio.create_task(coro)
        return self.loop.run_until_complete(coro)
        # return task.result()

    def run_and_get2(self, coro):
        task = asyncio.create_task(coro)
        self.loop.run_until_complete(task)
        return task.result()

    @property
    def debug(self):
        """ Return the `debug` property of `BaseMirobot` """
        return self._debug

    @debug.setter
    def debug(self, value):
        """
        Set the new value for the `debug` property of `mirobot.base_mirobot.BaseMirobot`. Use as in `BaseMirobot.setDebug(value)`.
        Use this setter method as it will also update the logging objects of `mirobot.base_mirobot.BaseMirobot` and its `mirobot.serial_device.SerialDevice`. As opposed to setting `mirobot.base_mirobot.BaseMirobot._debug` directly which will not update the loggers.

        Parameters
        ----------
        value : bool
            The new value for `mirobot.base_mirobot.BaseMirobot._debug`.

        """
        self._debug = bool(value)

    async def _find_address(self):
        devices = await discover()
        mirobot_bt = next((d for d in devices if d.name == 'QN-Mini6Axis'), None)
        if mirobot_bt is None:
            raise Exception('Could not find mirobot bt')

        return mirobot_bt.address

    def connect(self):
        async def start_connection():
            connection = await self.client.connect()
            # connection = await self.client.is_connected()

            services = await self.client.get_services()
            service = services.get_service("0000ffe0-0000-1000-8000-00805f9b34fb")

            self.characteristic = next((c for c in service.characteristics
                                        if c.uuid == '0000ffe1-0000-1000-8000-00805f9b34fb'), None)

            return connection

        self.connection = self.run_and_get(start_connection())

    def disconnect(self):
        self.run_and_get(self.client.disconnect())

    @property
    def is_connected(self):
        return self.connection

    def send(self, msg, disable_debug=False, wait=True, wait_idle=True):
        feedback = []
        ok_counter = 0

        def notification_handler(sender, data):
            """Simple notification handler which prints the data received."""
            nonlocal ok_counter, feedback
            data = data.decode()

            data_lines = re.findall(r".*[\r\n]{0,1}", data)
            for line in data_lines[:-1]:
                if self._debug and not disable_debug:
                    self.logger.debug(f"[RECV] {repr(line)}")

                if feedback and not feedback[-1].endswith('\r\n'):
                    feedback[-1] += line
                else:
                    if feedback:
                        feedback[-1] = feedback[-1].strip('\r\n')

                    feedback.append(line)

                if feedback[-1] == 'ok\r\n':
                    ok_counter += 1

                print(feedback)

        async def async_send(msg):
            nonlocal ok_counter, feedback
            if wait:
                await self.client.start_notify(self.characteristic.uuid, notification_handler)

            for s in chunks(bytes(msg + '\r\n', 'utf-8'), 20):
                await self.client.write_gatt_char(self.characteristic.uuid, s)

            if self._debug and not disable_debug:
                self.logger.debug(f"[SENT] {msg}")

            if wait:
                while ok_counter < 2:
                    print('waiting...', msg, ok_counter)
                    await asyncio.sleep(0.1)

                if wait_idle:
                    orig_feedback = feedback
                    while self.mirobot.status.state != 'Idle':
                        print(self.mirobot.status.state)
                        feedback = []
                        ok_counter = 0
                        await self.client.write_gatt_char(self.characteristic.uuid, b'?\r\n')
                        while ok_counter < 2:
                            print('waiting for idle...', msg, ok_counter)
                            await asyncio.sleep(0.1)
                        self.mirobot.status = self.mirobot._parse_status(feedback[0])

                    print('finished idle')
                    feedback = orig_feedback
                await self.client.stop_notify(self.characteristic.uuid)

        asyncio.run(async_send(msg))

        # if wait and wait_idle:
        #     print('waiting idly')
        #     self.wait_until_idle()
        #

        feedback[-1] = feedback[-1].strip('\r\n')
        return feedback

    def wait_until_idle(self, refresh_rate=0.1):
        """
        Continuously loops over and refreshes state of the Mirobot.
        It stops when it encounters an 'Idle' state string.

        Parameters
        ----------
        refresh_rate : float
            (Default value = `0.1`) The rate in seconds to check for the 'Idle' state. Choosing a low number might overwhelm the controller on Mirobot. Be cautious when lowering this parameter.

        Returns
        -------
        output : List[str]
            A list of output strings upto and including the terminal string.
        """
        print(self.mirobot.status.state)
        self.mirobot.update_status(disable_debug=False)

        while self.mirobot.status.state != 'Idle':
            print(self.mirobot.status.state)
            time.sleep(refresh_rate)
            self.mirobot.update_status(disable_debug=False)
