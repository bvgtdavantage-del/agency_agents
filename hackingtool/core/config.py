import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    timeout: int = 5
    max_threads: int = 100
    output_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "ht_output"))
    user_agent: str = "HackingTool/2.0 Security-Research-Framework"
    verify_ssl: bool = True
    verbose: bool = False
    target: Optional[str] = None

    def output_path(self, filename: str) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        return os.path.join(self.output_dir, filename)
