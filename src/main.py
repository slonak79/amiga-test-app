# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
import argparse
import asyncio
import os
from typing import List
from enum import Enum

# Must come before kivy imports
os.environ["KIVY_NO_ARGS"] = "1"

# gui configs must go before any other kivy import
from kivy.config import Config  # noreorder # noqa: E402

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


class VirtualJoystickApp(App):
    """Base class for the main Kivy app."""

    def __init__(self) -> None:
        super().__init__()
        self.hidden_button: bool = False
        self.async_tasks: List[asyncio.Task] = []

    def build(self):
        return Builder.load_file("res/main.kv")

    def on_exit_btn(self) -> None:
        """Kills the running kivy application."""
        App.get_running_app().stop()

    def on_action_button(self, action_button):
        if action_button.state == ACTION_BUTTON_STATE.NORMAL.value:
            action_button.text = ACTION_BUTTON_TEXT.START.value
            self.hidden_button = False
        else:
            action_button.text = ACTION_BUTTON_TEXT.STOP.value
            self.hidden_button = True

    async def app_func(self):
        async def run_wrapper() -> None:
            # we don't actually need to set asyncio as the lib because it is
            # the default, but it doesn't hurt to be explicit
            await self.async_run(async_lib="asyncio")
            for task in self.async_tasks:
                task.cancel()

        # Placeholder task
        self.async_tasks.append(asyncio.ensure_future(self.template_function()))

        return await asyncio.gather(run_wrapper(), *self.async_tasks)

    async def template_function(self) -> None:
        """Placeholder forever loop."""
        while self.root is None:
            await asyncio.sleep(0.01)

        while True:
            await asyncio.sleep(0.5)

            # increment the counter using internal libs and update the gui
            self.root.ids.disable_button.disabled = self.hidden_button


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="joystick-tutorial")

    # Add additional command line arguments here

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(VirtualJoystickApp().app_func())
    except asyncio.CancelledError:
        pass
    loop.close()
