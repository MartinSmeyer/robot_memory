import asyncio
import re
import time

from bleak import discover, BleakClient

from .exceptions import MirobotError, MirobotAlarm, MirobotReset


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

        self._run_and_get(self._ainit())

    async def _ainit(self, address=None, autofindaddress=True):
        # if address was not passed in and autofindaddress is set to true,
        # then autosearch for a bluetooth device
        if autofindaddress and address is None:
            self.address = await self._find_address()
            """ The default address to use when making connections. To override this on a individual basis, provide portname to each invocation of `BaseMirobot.connect`. """
        else:
            self.address = address

        self.client = BleakClient(self.address, loop=self.loop)

    def run_and_get(self, coro):
        return self.loop.run_until_complete(coro)

    @property
    def debug(self):
        """ Return the `debug` property of `mirobot.bluetooth_low_energy_interface.BluetoothLowEnergyInterface` """
        return self._debug

    @debug.setter
    def debug(self, value):
        """
        Set the new value for the `debug` property of `mirobot.bluetooth_low_energy_interface.BluetoothLowEnergyInterface`. Use as in `BluetoothLowEnergyInterface.setDebug(value)`.
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

            services = await self.client.get_services()
            service = services.get_service("0000ffe0-0000-1000-8000-00805f9b34fb")

            self.characteristics = [c.uuid for c in service.characteristics]

            return connection

        self.connection = self._run_and_get(start_connection())

    def disconnect(self):
        """ Disconnect from the Bluetooth Extender Box """
        async def async_disconnect():
            try:
                await self.client.disconnect()
            except AttributeError:
                '''
                File "/home/chronos/.local/lib/python3.7/site-packages/bleak/backends/bluezdbus/client.py", line 235, in is_connected
                    return await self._bus.callRemote(
                AttributeError: 'NoneType' object has no attribute 'callRemote'
                '''
                # don\t know why it happens, it shouldn't and doesn't in normal async flow
                # but if it complains that client._bus is None, then we're good, right...?
                pass

        self.run_and_get(async_disconnect())

    @property
    def is_connected(self):
        return self.connection

    def send(self, msg, disable_debug=False, wait=True, wait_idle=True):
        self.feedback = []
        self.ok_counter = 0
        self.disable_debug = disable_debug

        def notification_handler(sender, data):
            """Simple notification handler which prints the data received."""
            data = data.decode()

            data_lines = re.findall(r".*[\r\n]{0,1}", data)
            for line in data_lines[:-1]:
                if self._debug and not self.disable_debug:
                    self.logger.debug(f"[RECV] {repr(line)}")

                if self.feedback and not self.feedback[-1].endswith('\r\n'):
                    self.feedback[-1] += line
                else:
                    if self.feedback:
                        self.feedback[-1] = self.feedback[-1].strip('\r\n')

                    self.feedback.append(line)

                    last_line = self.feedback[-2]
                    if 'error' in last_line:
                        self.logger.error(MirobotError(last_line.replace('error: ', '')))

                    if 'ALARM' in last_line:
                        self.logger.error(MirobotAlarm(last_line.split('ALARM: ', 1)[1]))

                    if matches_eol_strings(reset_strings, last_line):
                        self.logger.error(MirobotReset('Mirobot was unexpectedly reset!'))

                if self.feedback[-1] == 'ok\r\n':
                    self.ok_counter += 1

        async def async_send(msg):
            async def write(msg):
                for c in self.characteristics:
                    await self.client.write_gatt_char(c, msg)

            if wait:
                for c in self.characteristics:
                    await self.client.start_notify(c, notification_handler)

            for s in chunks(bytes(msg + '\r\n', 'utf-8'), 20):
                await write(s)

            if self._debug and not disable_debug:
                self.logger.debug(f"[SENT] {msg}")

            if wait:
                while self.ok_counter < 2:
                    # print('waiting...', msg, self.ok_counter)
                    await asyncio.sleep(0.1)

                if wait_idle:
                    # really wish I could recursively call `send(msg)` here instead of
                    # replicating logic. Alas...
                    orig_feedback = self.feedback

                    async def check_idle():
                        self.disable_debug = True
                        self.feedback = []
                        self.ok_counter = 0
                        await write(b'?\r\n')
                        while self.ok_counter < 2:
                            # print('waiting for idle...', msg, self.ok_counter)
                            await asyncio.sleep(0.1)
                        self.mirobot.status = self.mirobot._parse_status(self.feedback[0])

                    await check_idle()

                    while self.mirobot.status.state != 'Idle':
                        # print(self.mirobot.status.state)
                        await check_idle()

                    # print('finished idle')
                    self.feedback = orig_feedback

                for c in self.characteristics:
                    await self.client.stop_notify(c)

        self._run_and_get(async_send(msg))

        self.feedback[-1] = self.feedback[-1].strip('\r\n')

        # the following bugs me so much, but I can't figure out why this is happening and needed:
        # Instant subsequent calls to `send_msg` hang, for some reason.
        # Like the second invocation doesn't start, it's gets stuck as `selector._poll` in asyncio
        # Putting a small delay fixes this but why...???
        time.sleep(0.1)

        return self.feedback
