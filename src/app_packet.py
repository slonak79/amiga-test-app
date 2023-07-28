from __future__ import annotations

import time
from enum import IntEnum

from struct import pack
from struct import unpack
from farm_ng.canbus.packet import Packet, AmigaControlState, DASHBOARD_NODE_ID
from farm_ng.canbus import canbus_pb2


class AmigalightState(IntEnum):
    STATE_ON = 1
    STATE_OFF = 0


class AmigaLight(Packet):
    cob_id = 0x180

    def __int__(
        self,
        state_req: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
        ligt_state: int = AmigalightState.STATE_OFF,
    ):
        self.format = "<BB6x"

        self.state_req = state_req
        self.ligt_state = ligt_state

        self.stamp_packet(time.monotonic())

    def encode(self):
        return pack(
            self.format,
            self.state_req,
            self.ligt_state,
        )

    def decode(self, data):
        (self.state_req, ligt_state) = unpack(self.format, data)
        self.ligt_state = self.ligt_state

    def __str__(self):
        return (
            f"AMIGA RPDO1 Request state {self.state_req} LIGHT state {self.ligt_state}"
        )


def make_amiga_light_msg(
    state_req: AmigaControlState, light_state: int = AmigalightState
) -> canbus_pb2.RawCanbusMessage:
    """Creates a canbus_pb2.RawCanbusMessage.

    Uses the AmigalightState structure and formatting, that can be sent
    directly to the canbus service to be formatted and send on the CAN bus.

    Args:
        state_req: State of the Amiga vehicle control unit (VCU).
        light_state: Command speed in meters per second.

    Returns:
        An instance of a canbus_pb2.RawCanbusMessage.
    """
    return canbus_pb2.RawCanbusMessage(
        id=AmigaLight.cob_id + DASHBOARD_NODE_ID,
        data=AmigaLight(state_req=state_req, light_state=light_state).encode(),
    )


def parse_amiga_light_message(
    message: canbus_pb2.RawCanbusMessage,
) -> AmigaLight | None:
    if message.id != AmigaLight.cob_id + DASHBOARD_NODE_ID:
        return None
    return AmigaLight.from_can_data(message.data, stamp=message.stamp)
