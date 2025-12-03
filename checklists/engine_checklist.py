"""
Map Pro Engine Development Checklist
Ensures all engines follow the required architectural pattern
"""

from pathlib import Path
from typing import Dict, List
from ...core.data_paths import map_pro_paths


class EngineChecklist:
    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self.engine_path = map_pro_paths.engines / engine_name
        
        self.required_files = [
            f"{engine_name}_coordinator.py",
            "__init__.py"
        ]
        
        self.coordinator_requirements = [
            "class {name}Coordinator",
            "def report_status_to_core",
            "def handle_market_communication", 
            "def validate_inputs",
            "def process_workflow"
        ]