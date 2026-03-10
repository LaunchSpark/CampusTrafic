import csv

from pipelineio.state import load_draft, save_draft
from py.world.connection import Connection
from py.world.device_trace import DeviceTrace

INPUTS = [
    "data/artifacts/world_drafts/01_empty.pkl",
    "data/raw/synthetic/splunk_synthetic_wap_events.csv",
]
OUTPUTS = ["data/artifacts/world_drafts/02_with_devices.pkl"]


def run() -> None:
    world = load_draft(INPUTS[0])
    csv_path = INPUTS[1]

    # Parse the Splunk CSV directly
    device_connections = {}

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wap_id = row.get("wap_id")
                device_id = row.get("device_id")

                if not device_id or not wap_id:
                    continue

                start_ts_str = row.get("start_ts_ms")
                end_ts_str = row.get("end_ts_ms")

                start_ts = int(start_ts_str) if start_ts_str else None
                end_ts = int(end_ts_str) if end_ts_str else None

                conn = Connection(node_id=wap_id, start_ts_ms=start_ts, end_ts_ms=end_ts)
                device_connections.setdefault(device_id, []).append(conn)
    except FileNotFoundError:
        print(f"File {csv_path} not found. Skipping device processing.")

    # Assign to world.devices
    devices = [
        DeviceTrace(device_id=d_id, connections=sorted(conns, key=lambda c: (c.start_ts_ms or 0, c.node_id)))
        for d_id, conns in device_connections.items()
    ]
    world.devices = devices

    save_draft(world, OUTPUTS[0])
