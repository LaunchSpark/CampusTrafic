"""
PIPELINE STEP: BASELINE TRANSITION MODEL (WITH TRAIN/TEST SPLIT + FLOW)
=======================================================================
Builds a transition probability model using 70% of the data,
and saves the remaining 30% for evaluation.

Adds:
- outbound_totals (magnitude per node)
- flow_matrix (expected transitions)
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import os
import random
from typing import Any

from pipelineio.state import load_draft, save_draft


@dataclass
class BaselineTransitionModel:
    # Directional metrics
    transition_counts: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    transition_probs: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    # New: magnitude
    outbound_totals: dict[str, int] = field(default_factory=dict)

    # New: flow (expected counts)
    flow_matrix: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    # Hourly metrics
    hourly_counts: dict[int, dict[str, dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )

    def process(
        self,
        journeys_data: Any,
        time_threshold_minutes: int = 120,
        progress_callback=None
    ) -> None:
        total_users = len(journeys_data.journeys)

        # -----------------------------
        # COUNT TRANSITIONS (TRAIN SET)
        # -----------------------------
        for idx, journey in enumerate(journeys_data.journeys):
            if progress_callback and idx % max(1, total_users // 25) == 0:
                progress_callback(idx / max(1, total_users) * 0.9)

            waypoints = journey.waypoints

            for i in range(len(waypoints) - 1):
                wp_a = waypoints[i]
                wp_b = waypoints[i + 1]

                time_diff_minutes = (wp_b.timestamp - wp_a.timestamp) / (1000.0 * 60.0)

                node_a = wp_a.wap_id
                node_b = wp_b.wap_id

                if node_a != node_b and time_diff_minutes <= time_threshold_minutes:
                    # Count transition
                    self.transition_counts[node_a][node_b] += 1

                    # Track total outbound volume
                    self.outbound_totals[node_a] = self.outbound_totals.get(node_a, 0) + 1

                    # Hourly tracking
                    try:
                        journey_hour = datetime.fromtimestamp(
                            wp_a.timestamp / 1000.0
                        ).hour
                        self.hourly_counts[journey_hour][node_a][node_b] += 1
                    except Exception:
                        pass

        # -----------------------------
        # CONVERT TO PROBABILITIES
        # -----------------------------
        for origin, destinations in self.transition_counts.items():
            total_outbound = sum(destinations.values())

            if total_outbound == 0:
                continue

            for destination, count in destinations.items():
                self.transition_probs[origin][destination] = count / total_outbound

        # -----------------------------
        # BUILD FLOW MATRIX
        # -----------------------------
        for origin, destinations in self.transition_probs.items():
            total = self.outbound_totals.get(origin, 0)

            for destination, prob in destinations.items():
                self.flow_matrix[origin][destination] = prob * total

        if progress_callback:
            progress_callback(0.99)

        # -----------------------------
        # CLEAN FOR PICKLING
        # -----------------------------
        self.transition_counts = {k: dict(v) for k, v in self.transition_counts.items()}
        self.transition_probs = {k: dict(v) for k, v in self.transition_probs.items()}
        self.flow_matrix = {k: dict(v) for k, v in self.flow_matrix.items()}
        self.outbound_totals = dict(self.outbound_totals)

        self.hourly_counts = {
            hour: {orig: dict(dests) for orig, dests in origin_data.items()}
            for hour, origin_data in self.hourly_counts.items()
        }

    def output(self, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_draft(self, output_path)

    @classmethod
    def load(cls, input_path: str) -> "BaselineTransitionModel":
        return load_draft(input_path)


# --- Paths ---
run_id = os.environ.get('PIPELINE_RUN_ID', 'EXAMPLE_RUN_ID')

INPUTS = [
    f'data/artifacts/runs/{run_id}/world/final_journeys.pkl'
]

OUTPUTS = [
    f'data/artifacts/runs/{run_id}/model_tree/baseline_transitions.pkl'
]


def run(
    is_synthetic: bool = False,
    time_threshold_minutes: int = 120,
    custom_param: int = 10,
    progress_callback=None
) -> None:
    target_input = INPUTS[0]
    target_output = OUTPUTS[0]

    if is_synthetic:
        target_input = target_input.replace('runs/' + run_id, 'synthetic_drafts')
        target_output = target_output.replace('runs/' + run_id, 'synthetic_drafts')

    # Load full dataset
    journeys_data = load_draft(target_input)

    # -----------------------------
    # TRAIN / TEST SPLIT
    # -----------------------------
    journeys = journeys_data.journeys

    random.seed(42)
    random.shuffle(journeys)

    split_idx = int(0.7 * len(journeys))
    train_journeys = journeys[:split_idx]
    test_journeys = journeys[split_idx:]

    print(f"Total journeys: {len(journeys)}")
    print(f"Train: {len(train_journeys)} | Test: {len(test_journeys)}")

    # Train model
    journeys_data.journeys = train_journeys

    model = BaselineTransitionModel()
    model.process(
        journeys_data,
        time_threshold_minutes=time_threshold_minutes,
        progress_callback=progress_callback
    )

    # Save model
    model.output(target_output)

    # Save test set
    test_output_path = target_output.replace(
        "baseline_transitions.pkl",
        "baseline_test_journeys.pkl"
    )

    journeys_data.journeys = test_journeys
    os.makedirs(os.path.dirname(test_output_path), exist_ok=True)
    save_draft(journeys_data, test_output_path)

    print(f"Saved test set to: {test_output_path}")