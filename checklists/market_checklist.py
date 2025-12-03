"""
Map Pro Market Implementation Checklist
Ensures all markets implement required interface correctly
"""

from pathlib import Path
from typing import Dict, List
from ...core.data_paths import map_pro_paths


class MarketChecklist:
    def __init__(self, market_name: str):
        self.market_name = market_name
        self.market_path = map_pro_paths.markets / market_name
        
        self.required_files = [
            f"{market_name}_searcher.py",
            f"{market_name}_downloader.py", 
            f"{market_name}_parser.py",
            f"{market_name}_mapper.py",
            f"{market_name}_workflow.py",
            f"{market_name}_validators.py",
            "__init__.py"
        ]
        
        self.interface_methods = [
            "search_entities",
            "search_filings", 
            "get_market_capabilities",
            "health_check"
        ]
    
    def check_market_compliance(self) -> Dict[str, bool]:
        """Check if market implementation is complete"""
        checks = {}
        
        # Check required files
        for req_file in self.required_files:
            file_path = self.market_path / req_file
            checks[f"has_{req_file}"] = file_path.exists()
        
        # Check interface implementation
        workflow_file = self.market_path / f"{self.market_name}_workflow.py"
        if workflow_file.exists():
            content = workflow_file.read_text()
            for method in self.interface_methods:
                checks[f"implements_{method}"] = method in content
        
        return checks
    
    def generate_checklist(self) -> str:
        """Generate market implementation checklist"""
        checks = self.check_market_compliance()
        
        checklist = f"MARKET IMPLEMENTATION CHECKLIST: {self.market_name.upper()}\n"
        checklist += "=" * 50 + "\n\n"
        
        checklist += "REQUIRED FILES:\n"
        for req_file in self.required_files:
            status = "[OK]" if checks.get(f"has_{req_file}", False) else "[FAIL]"
            checklist += f"  {status} {req_file}\n"
        
        checklist += "\nINTERFACE COMPLIANCE:\n"
        for method in self.interface_methods:
            status = "[OK]" if checks.get(f"implements_{method}", False) else "[FAIL]"
            checklist += f"  {status} {method} implemented\n"
        
        checklist += "\nMARKET-SPECIFIC REQUIREMENTS:\n"
        checklist += "  [ ] Success threshold defined in market_success_thresholds.py\n"
        checklist += "  [ ] Workflow uses only required core utilities\n"
        checklist += "  [ ] Market-specific error classification implemented\n"
        checklist += "  [ ] Validation rules for market data formats\n"
        checklist += "  [ ] Configuration file created in /config/markets/\n"
        
        return checklist