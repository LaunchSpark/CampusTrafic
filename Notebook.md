# Wi-Fi Mesh Traffic Analysis for Campus Spatial Optimization

**Mikel Gonzalez, Lucas Starkey, Trejan Gannod, Trigg Lampkins, Isaiah Chastain**

## 1. Problem Statement

This project studies whether anonymized Wi-Fi access point data can be used to estimate movement patterns inside Tennessee Tech University campus spaces. The immediate goal is to build a repeatable pipeline that turns raw WAP connection logs into interpretable traffic models and visual outputs that can support operational decisions.

The main research questions are:

- Can device-to-WAP association logs reveal meaningful daily and weekly pedestrian traffic patterns?
- Can those patterns support decisions such as cleaning schedules, event placement, and space utilization?
- Can the pipeline distinguish normal movement structure from unusual or residual traffic behavior?

The data source is campus Wi-Fi connection activity, represented in this repository as raw syslog-style events and synthetic drafts for safe development. Success is measured less by a single classification score and more by whether the pipeline can consistently produce:

- clean device traces,
- stable WAP-level and person-level world models,
- baseline movement predictions,
- residual views that expose anomalies or drift, and
- visualization-ready field outputs for downstream analysis.

## 2. Background and Related Work

Wi-Fi-based occupancy and movement analysis is a practical alternative to manual counting, surveys, and GPS tracking. Manual methods do not scale well, surveys are sparse and subjective, and GPS is often unavailable or too invasive for indoor environments. Wi-Fi infrastructure already exists in campus buildings, so it provides an attractive passive sensing layer for mobility analysis.

Prior work has shown that Wi-Fi probe and association data can support both aggregate movement studies and origin-destination style inference. These studies also identify recurring challenges: a single person may carry multiple devices, WAP handoffs can generate noisy transitions, and overlapping coverage areas can blur the boundary between actual movement and network behavior.

This project builds on those ideas but frames the work as a modular pipeline. Instead of stopping at occupancy counts, the repository is organized around phases that progressively build a world model, explore movement structure, train a baseline model, separate residual behavior, and render spatial outputs for evaluation and visualization.

## 3. Data and Exploratory Analysis

The data model in this repository is centered on device connection events. In `phase_01_build_world--Lucas_Starkey`, raw Wi-Fi observations are transformed into increasingly structured artifacts.

### Phase 01: Build World

#### Step 01: Build Devices

`step_01_build_devices.py` ingests raw logs and groups observations by device. Each device is converted into a chronologically ordered list of traces with:

- origin WAP,
- origin connection timestamp,
- destination WAP, and
- destination connection timestamp.

This step establishes the core movement record used by all later phases.

#### Step 02: Build WAP Index

`step_02_build_wap_index.py` reorganizes the device traces into a WAP-centric index. For each WAP, the step stores sorted timestamps, device identifiers, and trace references. This makes temporal lookup efficient and supports overlap analysis in the next step.

#### Step 03: Resolve People

`step_03_resolve_people.py` attempts to group sibling devices that likely belong to the same person. It compares devices that appear at the same WAP within a configurable time window and uses overlap scoring to assign a primary device identity. This addresses one of the main data quality problems in Wi-Fi analytics: inflated counts caused by multi-device ownership and MAC-level fragmentation.

#### Step 04: Build Graph

`step_04_build_graph.py` maps resolved identities back onto WAP visits to create a spatial graph representation. The resulting artifact tracks which primary identities visited each WAP and counts unique people per node. This graph becomes the canonical world-state output for the run.

### Exploratory Observations

The exploratory value of this phase is not only in visualization, but in checking whether the raw data can support the later modeling tasks. Important questions include:

- How many device observations survive ingestion and cleaning?
- Which WAPs dominate traffic volume?
- How often do overlapping devices appear to represent the same person?
- Are there suspiciously sparse or dense nodes that may indicate logging issues?

## 4. Methods and Tools

This section reflects both the current implementation in the repository and the corrected project direction from a later meeting. The current implementation is strongest in the pipeline orchestration and `phase_01_build_world--Lucas_Starkey`, while modeling and visualization remain planned extensions.

### 4.1 Data Collection

The primary intended data source for this study is anonymized Wi-Fi connection data collected from wireless access points (WAPs) distributed throughout Tennessee Tech University's campus. These logs are treated as a passive sensing mechanism for estimating pedestrian mobility without directly identifying individual people.

Each production connection record is expected to include:

- WAP ID,
- hashed or otherwise anonymized device ID,
- connection start timestamp, and
- connection end timestamp when available.

The intended deployment context assumes coordination with campus IT administration so that privacy, access control, and institutional data-governance requirements are satisfied. The pilot study remains focused on the Lab Science Commons (LSC) before any broader campus rollout.

In the current repository, this production data source is represented by local stand-in files under `data/raw/`, including a real-data path and a synthetic syslog path used for development and testing.

### 4.2 Data Preparation and Trace Construction

Raw connection logs must be transformed into device and person movement traces before any modeling can occur. The meeting summary identifies the main preprocessing goals as:

- timestamp normalization,
- filtering incomplete or corrupted records,
- resolving overlapping or ambiguous WAP associations,
- grouping device-level observations into person-level traces,
- and extracting node and time-interval features for later modeling.

That full preprocessing pipeline is not yet implemented end-to-end. What is implemented today in `phase_01_build_world--Lucas_Starkey` is a narrower but functional trace-construction workflow:

- `step_01_build_devices.py` ingests raw rows and groups them by device,
- device observations are sorted chronologically,
- ordered observations are folded into traces that link one WAP observation to the next,
- `step_02_build_wap_index.py` builds a WAP-centric index for fast temporal lookup,
- and `step_03_resolve_people.py` merges likely sibling devices using overlap windows at shared WAPs.

As a result, the current pipeline already approximates mobility traces of the form
`Device_i -> [(WAP_1, t1), (WAP_2, t2), (WAP_5, t3), ...]`, and then aggregates devices into person identities. However, it does not yet implement the full timestamp-normalization, data-cleaning, and feature-extraction workflow described in the meeting notes.

### 4.3 Spatial Graph Representation

The corrected meeting summary centers the project around a `World` object that contains two main components:

- a `Graph` used for movement structure and modeling,
- and a `Grid` used primarily for visualization.

This object is only partially implemented today. The `Graph` portion exists in the current codebase, while the `Grid` remains a later phase.

In the intended design, the graph organizes movement between waypoints or WAP locations. The system treats node location as a core feature, and the meeting notes describe later modeling outputs in terms of waypoint-level movement vectors and traffic intensity.

```text
WAP1 --- WAP2 --- WAP3
 |        |
WAP4 --- WAP5 --- WAP6
```

The current implementation is still more limited than that target design. `step_04_build_graph.py` builds a WAP-keyed visit structure that maps resolved identities onto WAP visits and records node-level unique-person counts. It does not yet implement the full `Grid` component or a mature waypoint graph used for continuous visualization.

### 4.4 Mobility Inference

The current direction of the project is to infer movement edges between waypoints from device connection sequences. Input Wi-Fi association events are first converted into device movement sequences and then aggregated into person movement traces. From those traces, the intended system extracts three main features for each node and time interval:

- node location,
- movement vector,
- and traffic intensity.

The graph component is intended to process device connection data into movement edges between waypoints. In practice, that means the final system should move from raw association records toward node-level and interval-level movement predictions rather than only device visit histories.

This target behavior is only partially implemented. The current repository builds traces and WAP-keyed visit structures, but it does not yet complete the full node-interval feature extraction and predictive movement-edge workflow described in the meeting summary.

### 4.5 Spatial Flow Field Construction

The visualization plan uses a grid generated from waypoint graph data. In that design, each node is associated with a movement vector representing pedestrian flow, and interpolation between nodes produces a continuous vector field across the environment.

The `Grid` component is meant to support this layer. Its primary role is visualization rather than modeling, and it is intended to hold the information needed to turn discrete waypoint predictions into an explorable flow map.

This layer remains planned rather than implemented. The current repository does not yet construct the `Grid` object, interpolate vector fields across space, or render a finished grid-based flow map in the frontend.

### 4.6 Temporal Pattern Modeling

The corrected meeting notes define a two-stage modeling plan: baseline models first, then machine-learning refinement.

The intended baseline strategy includes three candidate models:

- Baseline Model 1: average traffic for each hour across all days,
- Baseline Model 2: average traffic for each hour within each weekday,
- Baseline Model 3: grouped weekdays, with Monday-Wednesday, Tuesday-Thursday, Friday, and weekends treated separately.

After selecting the strongest baseline, the plan is to train a decision tree model on the residual error between predicted and actual values. The meeting summary also specifies that multiple tree models should be tested using combinations of node location, movement vector, traffic intensity, and day-of-week features.

The current repository does not yet implement these baseline models or the residual decision-tree stage in code. The baseline and residual phases remain scaffolds plus modeling notes, so this section describes the agreed modeling direction rather than completed functionality.

### 4.7 System Architecture

The project uses a pipeline-based architecture managed by `run.py`. Each stage of the workflow is broken into ordered step files with declared inputs and outputs. The pipeline computes hashes over source code, inputs, outputs, and hyperparameters so that unchanged steps can be skipped and cached artifacts reused rather than recomputed.

The current system implements the following pieces:

- `run.py` orchestrates pipeline execution,
- `pipeline/run_logic/ast_runner.py` manages step discovery, caching, and execution,
- `pipelineio` persists draft and run artifacts,
- FastAPI exposes routes for runs, world drafts, and training/status surfaces,
- and the React frontend provides data-loading and training placeholder pages.

The meeting notes position the `World` object as the central structural component of the system. In that intended architecture, all movement data and later modeling outputs would be organized through the `World`, with `Graph` supporting movement structure and `Grid` supporting visualization. The current repository only partially realizes that architecture.

### 4.8 Tools and Technologies

The current codebase clearly uses:

- Python for the pipeline and backend services,
- NumPy for indexed WAP and timestamp processing,
- FastAPI for API routes,
- React and Vite for the web frontend,
- Bootstrap for frontend styling,
- and Git-based repository collaboration.

The revised full pipeline is expected to expand beyond the current implementation. Candidate or planned tools include:

- additional preprocessing utilities for feature extraction,
- decision-tree modeling tools for residual learning,
- grid-based interpolation utilities for vector-field generation,
- and interactive spatial visualization libraries for traffic flow exploration.

Those tools should be described as planned additions to the full pipeline, not as components already used throughout the current repository.

### 4.9 Evaluation Strategy

The meeting summary defines success in terms of both predictive quality and interpretability. Quantitatively, the later modeling stages are intended to compare multiple baselines, select the strongest one, and then measure whether residual learning improves traffic prediction quality across nodes and time intervals.

Qualitatively, the final system should support interactive inspection of movement directions and traffic density, making the outputs understandable to project stakeholders rather than only to the modeling team.

These goals remain future-facing. The current implementation does not yet produce the node-level predicted traffic levels, direction vectors, or finished interactive flow maps needed for full evaluation.

## 5. Results

The current repository produces reliable pipeline and world-building artifacts but not yet the full predictive outputs described in the corrected meeting summary. The strongest completed results are that the system can:

- discover and run pipeline steps with caching,
- ingest synthetic or stand-in raw Wi-Fi log data,
- construct ordered device traces,
- build a WAP-centric index,
- resolve likely sibling devices into person-level identities,
- and export a final graph-like world artifact keyed by WAP visits.

Those results support the claim that the project has a functioning orchestration layer and a first-stage world-building backbone. They do not yet establish a completed `Grid` component, node-level movement predictions, baseline-model comparisons, decision-tree residual learning, or stakeholder-ready interactive flow visualization.

The current result is therefore foundational rather than predictive: the repository can build and cache intermediate movement structures, while the corrected meeting direction describes the next layers that still need to be implemented.

## 6. Conclusions and Future Work

This project has established a workable first-stage pipeline for campus Wi-Fi mobility analysis, and the corrected meeting summary clarifies the architectural direction. The current implementation shows that stand-in Wi-Fi logs can be transformed into structured traces, WAP indexes, resolved identities, and world artifacts under a reusable cached pipeline. That is a meaningful systems result, but it is still only the first layer of the intended platform.

The agreed next steps are:

- complete the `World` object by adding the `Grid` component,
- expand preprocessing and feature extraction for node-level and time-interval modeling,
- implement the three baseline traffic models,
- train and compare decision-tree residual models over the selected features,
- generate grid-based vector-field visualizations from waypoint data,
- and connect those outputs to the frontend for interactive exploration.

If those pieces are implemented, the project will move from a world-construction prototype to a full campus mobility analysis system aligned with the corrected meeting direction.

## 7. Appendix

Repository:

- `CampusTrafic` local project workspace
- [https://github.com/LaunchSpark/CampusTrafic](https://github.com/LaunchSpark/CampusTrafic)

Current implementation references:

- `run.py`
- `pipeline/phases/phase_01_build_world--Lucas_Starkey/steps/step_01_build_devices.py`
- `pipeline/phases/phase_01_build_world--Lucas_Starkey/steps/step_02_build_wap_index.py`
- `pipeline/phases/phase_01_build_world--Lucas_Starkey/steps/step_03_resolve_people.py`
- `pipeline/phases/phase_01_build_world--Lucas_Starkey/steps/step_04_build_graph.py`
- `api/main.py`
- `api/routes/`
- `website/web/src/routes/DataPage.jsx`
- `website/web/src/routes/TrainPage.jsx`

Planned-phase and architecture references:

- `pipeline/phases/phase_02_explore--Trigg_Lampkins/FLOW_README.md`
- `pipeline/phases/phase_02_explore--Trigg_Lampkins/ROUTING_README.md`
- `pipeline/phases/phase_03_baseline--Trey_Gannod/MODELING_README.md`
- `pipeline/phases/phase_04_residual--Isaiah_Chastain/MODELING_README.md`
- `pipeline/phases/phase_05_visualize--Mikel_Gonzalez/FIELD_README.md`
- `pipeline/phases/phase_05_visualize--Mikel_Gonzalez/EVAL_README.md`

Primary data and artifact locations:

- `data/raw/`
- `data/artifacts/`


#### LLM usage: 
    
