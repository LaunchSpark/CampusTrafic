"""
PIPELINE STEP TEMPLATE
======================

How to create a new pipeline step:
1. Copy this file into your target phase directory: `pipeline/phases/phase_XX_name/steps/step_YY_name.py`
2. Update the `INPUTS` and `OUTPUTS` lists with your desired artifact read/write paths.
3. Rename `YourDataClass` to represent the core anemic data structure you are building.
4. Write your business logic inside the methods of your dataclass.
5. Modify the `run()` function to accept your required hyperparameters.

About the Progress Bar:
-----------------------
If your step processes data in a loop and you want a live progress bar in the terminal:
1. Include `progress_callback=None` in your `run()` function signature.
2. Pass it down to your processing method.
3. Periodically call `progress_callback(float)` with a value between 0.0 and 1.0.
   Example: `progress_callback(current_idx / total_items)`
4. Best Practice: To prevent the UI drawing from slowing down your logic, only 
   trigger the callback every N iterations (e.g., `if idx % 50 == 0:`).

About Hyperparameters:
----------------------
Any arguments you add to the `run()` signature (except `progress_callback` and `is_synthetic`) 
will be automatically discovered by the orchestrator and appended to `PIPELINE_CONFIG` in `run.py`.

About Synthetic Data:
---------------------
The `is_synthetic` flag allows independent component testing. When True, the pipeline 
automatically replaces the `world_drafts` directory with `synthetic_drafts`. This lets you 
read/write mock data safely without polluting the main production cache.
"""

from typing import Any
from dataclasses import dataclass, field
import random
from datetime import datetime, timedelta
import os

# Define your anemic data structures here using @dataclass
@dataclass
class SyslogGenerator:
    log_lines: list[str] = field(default_factory=list)

    def process(self, num_lines: int = 1000, progress_callback=None) -> None:
        """
        Generates synthetic syslog data.
        Format: MMM DD HH:MM:SS <Access Point IP> ah_auth: <Client MAC Address>
        """
        ap_ips = [f"10.0.{i}.{j}" for i in range(1, 5) for j in range(1, 10)]
        macs = [f"00:1A:2B:{i:02X}:{j:02X}:{k:02X}" for i in range(1, 3) for j in range(1, 3) for k in range(1, 3)]
        
        start_date = datetime.now() - timedelta(days=1)
        
        for idx in range(num_lines):
            if progress_callback and idx % max(1, num_lines // 50) == 0:
                progress_callback(idx / max(1, num_lines))
                
            ap_ip = random.choice(ap_ips)
            # Add a slight bias to make some MACs more common
            mac = random.choice(macs) if random.random() > 0.1 else macs[0]
            
            start_date += timedelta(seconds=random.randint(1, 60))
            ts_str = start_date.strftime("%b %d %H:%M:%S")
            
            line = f"{ts_str} {ap_ip} ah_auth: {mac}"
            self.log_lines.append(line)

    def output(self, output_path: str) -> None:
        """Writes the generated text lines out to the file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for line in self.log_lines:
                f.write(line + "\n")

INPUTS = []
OUTPUTS = ['data/raw/synthetic/syslog.txt']

def run(num_lines: int = 1000, progress_callback=None) -> None:
    """
    The auto-discovered orchestrator entry point.
    Parameters defined here are strictly enforced against `run.py`'s PIPELINE_CONFIG.
    """
    target_output = OUTPUTS[0]
    
    data = SyslogGenerator()
    data.process(num_lines=num_lines, progress_callback=progress_callback)
    data.output(target_output)
