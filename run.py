from pipeline.run_logic import execute_pipeline

STEPS = [
    "01_init_world",
    "02_build_devices",
    "03_build_graph",
    "04_build_grid",
]

if __name__ == "__main__":
    execute_pipeline(STEPS)
