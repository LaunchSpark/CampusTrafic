from dataclasses import dataclass, field

import numpy as np

from pipelineio.state import load_draft, save_draft
from .step_01_build_devices import DeviceList, Trace


@dataclass
class WAPIndex:
    # wap_id -> (timestamps_array, device_ids_array, traceback_refs_array)
    index: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = field(default_factory=dict)

    def import_data(self, device_list: DeviceList) -> DeviceList:
        return device_list

    def build(self, device_list: DeviceList) -> None:
        """
        1. Flatten all traces from DeviceList into a WAP-centric dictionary
        2. Convert lists to numpy arrays for performance
        3. Sort by timestamp to enable O(log N) binary search for the People module
        """
        temp_wap_map: dict[str, list[tuple[int, str, Trace]]] = {}

        # 1. Gather traces by origin WAP
        for device_id, traces in device_list.devices.items():
            for trace in traces:
                wap_id = trace.originWap
                time_ms = trace.originConnectionTime

                if wap_id not in temp_wap_map:
                    temp_wap_map[wap_id] = []
                    
                temp_wap_map[wap_id].append((time_ms, device_id, trace))

        # 2 & 3. Sort chronologically and formalize into fast numpy arrays
        for wap_id, events in temp_wap_map.items():
            # Sort chronologically by connection time
            events.sort(key=lambda event: event[0])

            times = np.array([event[0] for event in events], dtype=np.int64)
            devices = np.array([event[1] for event in events], dtype=object)
            trace_refs = np.array([event[2] for event in events], dtype=object)

            self.index[wap_id] = (times, devices, trace_refs)

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "WAPIndex":
        return load_draft(input_path)


INPUTS = ['data/artifacts/world_drafts/01_device_list.pkl']
OUTPUTS = ['data/artifacts/world_drafts/02_wap_index.pkl']

def run(is_synthetic: bool = True) -> None:
    # Allow independent step testing by overriding inputs with static mock objects if synthetic
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]
    if is_synthetic:
        target_input = target_input.replace('world_drafts', 'synthetic_drafts')
        target_output = target_output.replace('world_drafts', 'synthetic_drafts')
        
    device_list = DeviceList.load(target_input)
    
    wap_index = WAPIndex()
    wap_index.import_data(device_list)
    wap_index.build(device_list)
    wap_index.output(target_output)
