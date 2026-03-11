import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pipelineio.state import load_draft, save_draft


@dataclass
class Trace:
    originWap: str
    originConnectionTime: int
    destinationWap: str | None = None
    destinationConnectionTime: int | None = None

    def __repr__(self) -> str:
        return f"Trace({self.originWap}@{self.originConnectionTime} -> {self.destinationWap}@{self.destinationConnectionTime})"


@dataclass
class DeviceList:
    devices: dict[str, list[Trace]] = field(default_factory=dict)

    def import_data(self, csv_path: Path | str) -> list[dict]:
        """Ingest raw signal CSVs into a flat list."""
        rows = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wap_id = row.get("wap_id")
                    device_id = row.get("device_id")
                    start_ts_str = row.get("start_ts_ms")

                    if not device_id or not wap_id or not start_ts_str:
                        continue

                    rows.append(
                        {
                            "device_id": device_id,
                            "wap_id": wap_id,
                            "start_ts_ms": int(start_ts_str),
                        }
                    )
        except FileNotFoundError:
            print(f"File {csv_path} not found. Skipping device processing.")

        return rows

    def process(self, raw_rows: list[dict]) -> None:
        """
        1. Explode to dict{deviceId: [connectionRecord]}
        2. Sort each device's records chronologically.
        3. Fold into Trace objects connecting A -> B.
        """
        # Step 1 & 2
        grouped = defaultdict(list)
        for row in raw_rows:
            grouped[row["device_id"]].append((row["wap_id"], row["start_ts_ms"]))

        # Step 3 & 4
        for device_id, records in grouped.items():
            records.sort(key=lambda x: x[1])  # sort by connectionTime
            
            traces = []
            for i in range(len(records)):
                origin_wap, origin_time = records[i]
                
                dest_wap = None
                dest_time = None
                if i + 1 < len(records):
                    dest_wap, dest_time = records[i + 1]

                traces.append(
                    Trace(
                        originWap=origin_wap,
                        originConnectionTime=origin_time,
                        destinationWap=dest_wap,
                        destinationConnectionTime=dest_time,
                    )
                )
                
            self.devices[device_id] = traces

    def output(self, output_path: str) -> None:
        """Saves to artifacts directory using the pipelineio schema"""
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "DeviceList":
        return load_draft(input_path)


INPUTS = ['data/raw/synthetic/splunk_synthetic_wap_events.csv']
OUTPUTS = ['data/artifacts/world_drafts/01_device_list.pkl']

def run(is_synthetic: bool = True) -> None:
    # Dynamically route to either synthetic or real datasets based on hyperparameter
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]
    if is_synthetic:
        target_output = target_output.replace('world_drafts', 'synthetic_drafts')
    else:
        target_input = target_input.replace('/synthetic/', '/real/')
        
    device_list = DeviceList()
    raw_csv_rows = device_list.import_data(target_input)
    device_list.process(raw_csv_rows)
    device_list.output(target_output)
