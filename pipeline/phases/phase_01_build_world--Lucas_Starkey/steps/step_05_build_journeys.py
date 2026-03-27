from collections import defaultdict
from dataclasses import dataclass, field
import datetime
import os
from typing import List, Dict

from pipelineio.state import load_draft, save_draft
from .step_01_build_devices import DeviceList, Trace
from .step_03_resolve_people import People


@dataclass
class Waypoint:
    wap_id: str
    timestamp: float
    is_stay: bool = False
    is_inferred: bool = False

@dataclass
class Journey:
    person_id: str
    waypoints: List[Waypoint] = field(default_factory=list)

@dataclass
class JourneysData:
    journeys: List[Journey] = field(default_factory=list)

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "JourneysData":
        return load_draft(input_path)


INPUTS = [
    'data/artifacts/world_drafts/01_device_list.pkl', 
    'data/artifacts/world_drafts/03_people.pkl'
]

run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')
OUTPUTS = [f'data/artifacts/runs/{run_id}/world/05_raw_journeys.pkl']


def run(stay_threshold_mins: float = 7.0, progress_callback=None, **kwargs):
    device_list: DeviceList = load_draft(INPUTS[0])
    people: People = load_draft(INPUTS[1])
    
    journeys_data = JourneysData()
    stay_budget_ms = stay_threshold_mins * 60 * 1000
    
    # Group raw device traces by canonical Person identity
    grouped_traces = defaultdict(list)
    for device_id, traces in device_list.devices.items():
        person_id = people.identityMap.get(device_id, device_id)
        grouped_traces[person_id].extend(traces)

    for person_id, person_traces in grouped_traces.items():
        person_traces.sort(key=lambda t: t.originConnectionTime)
        
        current_journey = Journey(person_id=person_id)
        
        for i, trace in enumerate(person_traces):
            wp = Waypoint(wap_id=trace.originWap, timestamp=trace.originConnectionTime, is_stay=False)
            current_journey.waypoints.append(wp)
            
            if trace.destinationWap is not None:
                current_journey.waypoints.append(Waypoint(
                    wap_id=trace.destinationWap, 
                    timestamp=trace.destinationConnectionTime, 
                    is_stay=False
                ))

        # Perform implicit stay detection
        for i in range(len(current_journey.waypoints) - 1):
            wp = current_journey.waypoints[i]
            next_wp = current_journey.waypoints[i+1]
            
            # If the gap between two pings is large, they stayed at the first WAP
            if (next_wp.timestamp - wp.timestamp) >= stay_budget_ms:
                wp.is_stay = True
                
        # Last node is a stay if it's the end of their recorded timeline
        if len(current_journey.waypoints) > 0:
            current_journey.waypoints[-1].is_stay = True

        journeys_data.journeys.append(current_journey)

    journeys_data.output(OUTPUTS[0])
