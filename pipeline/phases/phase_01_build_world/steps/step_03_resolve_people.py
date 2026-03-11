from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from pipelineio.state import load_draft, save_draft
from pipeline.phases.phase_01_build_world.steps.step_01_build_devices import DeviceList
from pipeline.phases.phase_01_build_world.steps.step_02_build_wap_index import WAPIndex


@dataclass
class Person:
    name: str
    deviceList: list[str]
    primaryDevice: str
    numDevices: int = 0
    deviceToPersonRatio: float = 0.0


@dataclass
class People:
    def __init__(self):
        self.people: list[Person] = []
        self.identityMap: dict[str, str] = {}
        
    def import_data(self, device_list: DeviceList, wap_index: WAPIndex) -> tuple[DeviceList, WAPIndex]:
        return device_list, wap_index

    def clean(self, device_list: DeviceList, wap_index: WAPIndex, threshold_minutes: float = 5.0, overlap_threshold: float = 0.8, progress_callback=None) -> None:
        """
        Groups sibling devices under a single Person identity to resolve MAC randomization.
        """
        threshold_ms = int(threshold_minutes * 60000)
        
        # 1. Sort Device_Index by trace count (descending)
        all_devices = sorted(
            list(device_list.devices.keys()),
            key=lambda d: len(device_list.devices[d]),
            reverse=True,
        )

        # We will use identityMap to track if a device has already been claimed by a Person.
        # Person objects will be created when a device has no parents, and it becomes the primary.
        
        # Helper dictionary to quickly find the Person object by its primary device ID
        primary_to_person: dict[str, Person] = {}

        for idx, device_id in enumerate(all_devices):
            if progress_callback and idx % max(1, len(all_devices) // 50) == 0:
                progress_callback(idx / max(1, len(all_devices)))

            # If it's already a child of someone else, skip (prevents chaining)
            if device_id in self.identityMap and self.identityMap[device_id] != device_id:
                continue

            traces = device_list.devices[device_id]
            if not traces:
                # No traces, instantiate as an independent Person
                new_person = Person(
                    name=f"Person_{len(self.people) + 1}",
                    deviceList=[device_id],
                    primaryDevice=device_id,
                    numDevices=1,
                    deviceToPersonRatio=1.0
                )
                self.people.append(new_person)
                primary_to_person[device_id] = new_person
                self.identityMap[device_id] = device_id
                continue

            scores: dict[str, int] = defaultdict(int)

            # 2. Window Search via np.searchsorted against WAP_Index
            for trace in traces:
                wap_id = trace.originWap
                time_ms = trace.originConnectionTime

                wap_data = wap_index.index.get(wap_id)
                if not wap_data:
                    continue

                times, devices, _ = wap_data
                
                if times.size == 0:
                    continue

                idx_start = int(np.searchsorted(times, time_ms - threshold_ms, side="left"))
                idx_end = int(np.searchsorted(times, time_ms + threshold_ms, side="right"))
                
                potential_parents = set(devices[idx_start:idx_end])

                for candidate in potential_parents:
                    if candidate == device_id:
                        continue
                        
                    # We are looking for a BestParent. A valid parent must be a primary device
                    # i.e. it must either already be a Person.primaryDevice OR it's not mapped yet.
                    # We ignore candidates that are already children (prevents chaining).
                    if candidate in self.identityMap and self.identityMap[candidate] != candidate:
                        continue
                        
                    scores[candidate] += 1

            # 3. Score similarity; select BestParent (highest overlap)
            best_parent = None
            if scores:
                best_score = max(scores.values())
                best_candidates = [c for c, sq in scores.items() if sq == best_score]
                
                # Require configured overlap_threshold relative to this device's traces to tether
                match_ratio = best_score / max(1, len(traces))
                if match_ratio >= overlap_threshold:
                    # Break ties by picking the candidate with the most overall traces
                    ranked = sorted(best_candidates, key=lambda c: len(device_list.devices[c]), reverse=True)
                    best_parent = ranked[0]

            if best_parent:
                if device_id in primary_to_person:
                    # i is already a primary device, BestParent takes over
                    person_obj = primary_to_person[device_id]
                    person_obj.primaryDevice = best_parent
                    
                    if best_parent not in person_obj.deviceList:
                        person_obj.deviceList.append(best_parent)
                        person_obj.numDevices += 1
                        person_obj.deviceToPersonRatio = 1.0 / person_obj.numDevices
                        
                    self.identityMap[device_id] = best_parent
                    self.identityMap[best_parent] = best_parent
                    primary_to_person[best_parent] = person_obj
                else:
                    # If BestParent is independent (not instantiated yet), instantiate new Person first
                    if best_parent not in primary_to_person:
                        new_person = Person(
                            name=f"Person_{len(self.people) + 1}",
                            deviceList=[best_parent],
                            primaryDevice=best_parent,
                            numDevices=1,
                            deviceToPersonRatio=1.0
                        )
                        self.people.append(new_person)
                        primary_to_person[best_parent] = new_person
                        self.identityMap[best_parent] = best_parent

                    # Add device (i) to BestParent's Person object
                    parent_person = primary_to_person[best_parent]
                    if device_id not in parent_person.deviceList:
                        parent_person.deviceList.append(device_id)
                        parent_person.numDevices += 1
                        parent_person.deviceToPersonRatio = 1.0 / parent_person.numDevices
                    
                    # 4. Remove device (i) from master list (hides child, prevents chaining) 
                    # Handled by setting it in identityMap.
                    self.identityMap[device_id] = best_parent

            else:
                # No valid parent found, it's its own master
                new_person = Person(
                    name=f"Person_{len(self.people) + 1}",
                    deviceList=[device_id],
                    primaryDevice=device_id,
                    numDevices=1,
                    deviceToPersonRatio=1.0
                )
                self.people.append(new_person)
                primary_to_person[device_id] = new_person
                self.identityMap[device_id] = device_id

    def process(self) -> None:
        """Post-clean metadata processing if needed."""
        pass

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "People":
        return load_draft(input_path)


INPUTS = ['data/artifacts/world_drafts/01_device_list.pkl', 'data/artifacts/world_drafts/02_wap_index.pkl']
OUTPUTS = ['data/artifacts/world_drafts/03_people.pkl']

def run(is_synthetic: bool = True, threshold_minutes: float = 5.0, overlap_threshold: float = 0.8, progress_callback=None) -> None:
    # Allow independent step testing by overriding inputs with static mock objects if synthetic
    target_input_1 = INPUTS[0]
    target_input_2 = INPUTS[1]
    target_output = OUTPUTS[0]
    
    if is_synthetic:
        target_input_1 = target_input_1.replace('world_drafts', 'synthetic_drafts')
        target_input_2 = target_input_2.replace('world_drafts', 'synthetic_drafts')
        target_output = target_output.replace('world_drafts', 'synthetic_drafts')

    device_list = DeviceList.load(target_input_1)
    wap_index = WAPIndex.load(target_input_2)
    
    people = People()
    people.import_data(device_list, wap_index)
    
    people.clean(device_list, wap_index, threshold_minutes=threshold_minutes, overlap_threshold=overlap_threshold, progress_callback=progress_callback)
    people.process()
    people.output(target_output)
