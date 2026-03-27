from collections import defaultdict
from dataclasses import dataclass, field
import datetime
import os
from typing import List, Dict

from pipelineio.state import load_draft, save_draft
from .step_04_build_graph import Graph
from .step_05_build_journeys import JourneysData, Journey, Waypoint


@dataclass
class RoutingModel:
    empirical_edge_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    empirical_edge_times: dict[str, dict[str, list]] = field(default_factory=dict)

@dataclass
class InterpolatedJourneysData:
    journeys: list[Journey] = field(default_factory=list)
    model: RoutingModel = field(default_factory=RoutingModel)

    def output(self, output_path: str) -> None:
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "InterpolatedJourneysData":
        return load_draft(input_path)


INPUTS = [
    'data/artifacts/runs/EXAMPLE_RUN_ID/world/05_raw_journeys.pkl',
    'data/artifacts/runs/EXAMPLE_RUN_ID/world/final_graph.pkl'
]

run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')
OUTPUTS = [f'data/artifacts/runs/{run_id}/world/final_journeys.pkl']


def is_adjacent(physical_edges: Dict[str, Dict[str, float]], n1: str, n2: str) -> bool:
    return n1 in physical_edges and n2 in physical_edges[n1]

def dfs_time_bounded(
    start_node: str, 
    end_node: str, 
    time_budget: float, 
    adj_matrix: Dict[str, Dict[str, float]], 
    empirical_times: Dict[str, Dict[str, list]],
    path: List[str], 
    current_time: float, 
    all_valid_paths: List[List[str]],
    eval_state: dict
):
    # Hard cap on recursive iterations to prevent hanging on disconnected graphs
    if eval_state["count"] > 2000:
        return
    eval_state["count"] += 1
    
    # Hard cap on permutations to prevent exponential explosion on dense graphs
    if len(all_valid_paths) >= 20:
        return
        
    # Add physical slack for fast walkers and signal latency (50% headroom or 2 mins)
    if current_time > max(time_budget * 1.5, time_budget + 120_000):
        return
        
    if start_node == end_node:
        all_valid_paths.append(list(path))
        return
        
    if start_node not in adj_matrix:
        return
        
    for neighbor in adj_matrix[start_node]:
        if neighbor in path:
            continue
            
        # Use empirical time if available, otherwise fallback to SVG prior length
        if start_node in empirical_times and neighbor in empirical_times[start_node]:
            # Take the average empirical crossing time
            hop_time = sum(empirical_times[start_node][neighbor]) / len(empirical_times[start_node][neighbor])
        else:
            hop_time = adj_matrix[start_node][neighbor]
            
        path.append(neighbor)
        dfs_time_bounded(neighbor, end_node, time_budget, adj_matrix, empirical_times, path, current_time + hop_time, all_valid_paths, eval_state)
        path.pop()


def run(progress_callback=None, **kwargs):
    raw_journeys_data: JourneysData = load_draft(INPUTS[0].replace('EXAMPLE_RUN_ID', run_id))
    graph: Graph = load_draft(INPUTS[1].replace('EXAMPLE_RUN_ID', run_id))
    
    adj_matrix = graph.physical_edges
    
    routing = RoutingModel()
    empirical_counts = defaultdict(lambda: defaultdict(int))
    empirical_times = defaultdict(lambda: defaultdict(list))
    
    interpolated_data = InterpolatedJourneysData()
    interpolated_data.journeys = raw_journeys_data.journeys
    
    # Needs Teleportation resolving Queue
    deferred_resolution_queue = []
    
    # PASS 1: Generate Empirical Edge Votes from observed reality
    for j_idx, journey in enumerate(interpolated_data.journeys):
        has_teleportation = False
        
        for i in range(len(journey.waypoints) - 1):
            wp = journey.waypoints[i]
            next_wp = journey.waypoints[i+1]
            
            if wp.wap_id == next_wp.wap_id:
                continue
                
            if is_adjacent(adj_matrix, wp.wap_id, next_wp.wap_id):
                # Tallied! Ground truth observation
                empirical_counts[wp.wap_id][next_wp.wap_id] += 1
                empirical_times[wp.wap_id][next_wp.wap_id].append(next_wp.timestamp - wp.timestamp)
            else:
                has_teleportation = True
                
        if has_teleportation:
            deferred_resolution_queue.append((j_idx, journey))
            
    # Sort the resolution queue by length so we resolve simpler traces first, adding their inferred paths to the community tallies
    deferred_resolution_queue.sort(key=lambda item: len(item[1].waypoints), reverse=True)
    
    # PASS 2: Bounded Empirical Teleportation Inference
    for j_idx, journey_ref in deferred_resolution_queue:
        shards = []
        current_shard = []
        
        for i in range(len(journey_ref.waypoints) - 1):
            wp = journey_ref.waypoints[i]
            next_wp = journey_ref.waypoints[i+1]
            current_shard.append(wp)
            
            if wp.wap_id == next_wp.wap_id:
                continue
                
            if not is_adjacent(adj_matrix, wp.wap_id, next_wp.wap_id):
                gap_time = next_wp.timestamp - wp.timestamp
                
                # If gap is larger than 30 minutes, don't try to interpolate walking paths
                if gap_time > (30 * 60 * 1000):
                    shards.append(current_shard)
                    current_shard = []
                    continue
                
                # Bounded DFS
                valid_paths = []
                dfs_time_bounded(
                    wp.wap_id, next_wp.wap_id, gap_time, 
                    adj_matrix, empirical_times, 
                    [wp.wap_id], 0.0, valid_paths, {"count": 0}
                )
                
                if valid_paths:
                    # Score paths physically and empirically
                    scored_paths = []
                    for path in valid_paths:
                        pop_score = 0
                        for pi in range(len(path)-1):
                            pop_score += empirical_counts[path[pi]][path[pi+1]]
                        scored_paths.append((pop_score, len(path), path))
                    
                    # Sort primarily by popularity (desc), then shortest path length (asc)
                    scored_paths.sort(key=lambda item: (item[0], -item[1]), reverse=True)
                    best_path = scored_paths[0][2]
                    
                    # Interpolate timestamps linearly
                    gap_per_hop = gap_time / (len(best_path) - 1)
                    
                    # Insert the path string
                    for step_idx in range(1, len(best_path) - 1):
                        inferred_wp = Waypoint(
                            wap_id=best_path[step_idx],
                            timestamp=wp.timestamp + (gap_per_hop * step_idx),
                            is_stay=False,
                            is_inferred=True
                        )
                        current_shard.append(inferred_wp)
                        
                        # Weakly reinforce inferred edges inside the routing model
                        empirical_counts[best_path[step_idx-1]][best_path[step_idx]] += 1
                else:
                    # Interpolation failed! Break the journey here
                    shards.append(current_shard)
                    current_shard = []
                    
        # Always append the terminating node
        current_shard.append(journey_ref.waypoints[-1])
        if current_shard:
            shards.append(current_shard)
            
        journey_ref._shards = shards
    
    # PASS 3: Generate the shattered, finalized dataset
    finalized_journeys = []
    for journey in interpolated_data.journeys:
        if hasattr(journey, '_shards'):
            for shard_wps in journey._shards:
                if len(shard_wps) > 1: # Strip out un-analyzable single-point journeys
                    new_j = Journey(person_id=journey.person_id)
                    new_j.waypoints = shard_wps
                    finalized_journeys.append(new_j)
        else:
            finalized_journeys.append(journey)
            
    interpolated_data.journeys = finalized_journeys
    
    # Finalize dictionaries for output
    routing.empirical_edge_counts = {k: dict(v) for k, v in empirical_counts.items()}
    routing.empirical_edge_times = {k: dict(v) for k, v in empirical_times.items()}
    interpolated_data.model = routing
    
    interpolated_data.output(OUTPUTS[0])
