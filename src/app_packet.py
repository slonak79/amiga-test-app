from __future__ import annotations

import time
from enum import IntEnum

from struct import pack
from struct import unpack
from farm_ng.canbus.packet import packet, AmigaControlState, DASHBOARD_NODE_ID
from farm_ng.canbus import canbus_pb2


class AmigalightState(IntEnum):
    STATE_ON = 1
    STATE_OFF = 0


class AmigaLight(packet):
    cob_id = 0x180

    def __int__(
            self,
            state_req: AmigaControlState = AmigaControlState.STATE_ESTOPPED,
            ligt_state: int = AmigalightState.STATE_OFF
    ):
        self.format = "<BhhBBx"

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
        return f"AMIGA RPDO1 Request state {self.state_req} LIGHT state {self.ligt_state}"


def make_amiga_light_msg(
        state_req: AmigaControlState, 
        light_state: int = AmigalightState
) -> canbus_pb2.RawCanbusMessage:
    return canbus_pb2.RawCanbusMessage(
        id=AmigaLight.cob_id + DASHBOARD_NODE_ID,
        data=AmigaLight(
            state_req=state_req,
            light_state=light_state
        ).encode()
    )


def parse_amiga_light_message(message: canbus_pb2.RawCanbusMessage) -> AmigaLight | None:
    if message.id != AmigaLight.cob_id + DASHBOARD_NODE_ID:
        return None
    return AmigaLight.from_can_data(message.data, stamp=message.stamp)
