# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
import argparse
import asyncio
import os
from typing import List
from enum import Enum
from functools import partial

from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.service.service_client import ClientConfig

import grpc
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.packet import MotorState
from farm_ng.service import service_pb2
from farm_ng.canbus.packet import make_amiga_rpdo1_proto
from farm_ng.canbus.packet import AmigaControlState
from app_packet import make_amiga_light_msg, AmigalightState

# Must come before kivy imports
os.environ["KIVY_NO_ARGS"] = "1"

# gui configs must go before any other kivy import
from kivy.config import Config  # noreorder # noqa: E402
from kivy.clock import Clock  # noreorder # noqa: E402


Config.set("graphics", "resizable", False)
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "800")
Config.set("graphics", "fullscreen", "false")
Config.set("input", "mouse", "mouse,disable_on_activity")
Config.set("kivy", "keyboard_mode", "systemanddock")

# kivy imports
from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402


# start/stop button
class ACTION_BUTTON_STATE(Enum):
    NORMAL = "normal"
    DOWN = "down"


class ACTION_BUTTON_TEXT(Enum):
    START = "START"
    STOP = "STOP"


t = 5

check = 0


class VirtualJoystickApp(App):
    """Base class for the main Kivy app."""

    def __init__(self, address: str, canbus_port: int) -> None:
        super().__init__()
        self.address: str = address
        self.canbus_port: int = canbus_port

        self.action_button: bool = False
        self.canbus_servie: bool = True  # default true

        self.time_to_start_label: str = "5"
        self.timer_text: str = "5"
        self.timer_check: int = t

        self.label_message: str = "label here"
        self.async_tasks: List[asyncio.Task] = []
        self.max_speed: float = 1.0
        self.max_angular_rate: float = 0
        self.set_speed: float = 1.0

    def build(self):
        return Builder.load_file("res/main.kv")

    def on_exit_btn(self) -> None:
        """Kills the running kivy application."""
        App.get_running_app().stop()

    def timer_callback(self, dt):
        global t
        if t > 0:
            t -= 1
            self.timer_text = str(t)
        if t <= 0:
            Clock.schedule_once(self.stop_timer, 1)
            Clock.schedule_once(self.clear_timer_values, 1.1)

    def start_timer(self):
        Clock.schedule_interval(self.timer_callback, 1)

    def stop_timer(self, dt):
        Clock.unschedule(self.timer_callback)
        self.root.ids.timer_popup.dismiss()

    def clear_timer_values(self, dt):
        global t
        t = self.timer_check
        self.timer_text = str(self.timer_check)

    def on_action_button(self, action_button):
        try:
            if action_button.state == ACTION_BUTTON_STATE.NORMAL.value:
                action_button.text = ACTION_BUTTON_TEXT.START.value
                # self.stop_timer()
                self.action_button = False
            else:
                action_button.text = ACTION_BUTTON_TEXT.STOP.value
                # self.start_timer()
                self.root.ids.timer_popup.open()
                self.action_button = True
        except Exception as ex:
            print(ex)

    def on_checkbox(self, active, value):
        if active:
            self.time_to_start_label = str(value)
            self.timer_text = str(value)
            self.timer_check = value

    def on_speed_slider(self, *speed_slider):
        self.set_speed = float(speed_slider[1])

    async def app_func(self):
        async def run_wrapper() -> None:
            # we don't actually need to set asyncio as the lib because it is
            # the default, but it doesn't hurt to be explicit
            await self.async_run(async_lib="asyncio")
            for task in self.async_tasks:
                task.cancel()

        # configure the canbus client
        canbus_config: ClientConfig = ClientConfig(
            address=self.address, port=self.canbus_port
        )
        canbus_client: CanbusClient = CanbusClient(canbus_config)

        # Placeholder task
        self.async_tasks.append(asyncio.ensure_future(self.template_function()))

        self.async_tasks.append(
            asyncio.ensure_future(self.send_can_msgs(canbus_client))
        )

        return await asyncio.gather(run_wrapper(), *self.async_tasks)

    async def send_can_msgs(self, client: CanbusClient) -> None:
        """This task ensures the canbus client sendCanbusMessage method has the pose_generator it will use to send
        messages on the CAN bus to control the Amiga robot."""
        while self.root is None:
            await asyncio.sleep(0.01)

        response_stream = None
        while self.action_button:
            # check the state of the service
            state = await client.get_state()

            # Wait for a running CAN bus service
            # TODO REVERT to !=

            if state.value not in [
                service_pb2.ServiceState.RUNNING,
                service_pb2.ServiceState.IDLE,
            ]:
                # Cancel existing stream, if it exists
                if response_stream is not None:
                    response_stream.cancel()
                    response_stream = None
                self.label_message = "Waiting for running canbus service..."
                self.canbus_servie = True
                print("Waiting for running canbus service...")
                await asyncio.sleep(0.1)
                continue
            else:
                self.canbus_servie = False
                self.label_message = "Canbus service ready."

            if response_stream is None:
                self.label_message = "Start sending CAN messages"
                print("Start sending CAN messages")
                response_stream = client.stub.sendCanbusMessage(self.pose_generator())

            try:
                async for response in response_stream:
                    # Sit in this loop and wait until canbus service reports back it is not sending
                    assert response.success
            except Exception as e:
                print(e)
                response_stream.cancel()
                response_stream = None
                continue

            await asyncio.sleep(0.1)

    async def pose_generator(self, period: float = 0.02):
        """The pose generator yields an AmigaRpdo1 (auto control command) for the canbus client to send on the bus
        at the specified period (recommended 50hz) based on the onscreen joystick position.
        """

        while self.root is None:
            await asyncio.sleep(0.01)

        while True:
            msg: canbus_pb2.RawCanbusMessage = make_amiga_rpdo1_proto(
                state_req=AmigaControlState.STATE_AUTO_ACTIVE,
                cmd_speed=self.max_speed,
                cmd_ang_rate=self.max_angular_rate,
            )
            # light_msg: canbus_pb2.RawCanbusMessage = make_amiga_light_msg(
            #     state_req=AmigaControlState.STATE_AUTO_ACTIVE,
            #     light_state=AmigalightState.STATE_ON,
            # )

            # Message to wheels
            yield canbus_pb2.SendCanbusMessageRequest(message=msg)
            # Message to light micro-controller
            # yield canbus_pb2.SendCanbusMessageRequest(message=light_msg)

            await asyncio.sleep(period)

    async def template_function(self) -> None:
        """Placeholder forever loop."""
        while self.root is None:
            await asyncio.sleep(0.01)

        while True:
            await asyncio.sleep(0.1)

            # update the gui

            self.root.ids.canbus_state_label.text = self.label_message
            self.root.ids.time_to_start_label.text = self.time_to_start_label
            self.root.ids.timer_label.text = self.timer_text
            self.root.ids.timer_label_v.text = self.timer_text
            # self.root.ids.action_button.disabled = self.canbus_servie


# use wheel speed to test sending message.
# when feather sees message turn LED to Green on state.
# when no message turn LED Red to indicate off state.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="joystick-tutorial")
    parser.add_argument(
        "--address", type=str, default="localhost", help="The server address"
    )
    parser.add_argument(
        "--canbus-port",
        type=int,
        default=50060,
        help="The grpc port where the canbus service is running.",
    )
    # Add additional command line arguments here
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            VirtualJoystickApp(args.address, args.canbus_port).app_func()
        )
    except asyncio.CancelledError:
        pass
    loop.close()
