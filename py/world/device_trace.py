from __future__ import annotations

from dataclasses import dataclass, field

from py.world.connection import Connection
from py.world.types import DeviceId


@dataclass
class DeviceTrace:
    device_id: DeviceId
    connections: list[Connection] = field(default_factory=list)

