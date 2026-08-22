"""
HackingTool - All-in-One Security Research Framework

For authorized security testing, CTF challenges, and educational use only.
Always obtain proper authorization before testing any system you do not own.
"""

import logging

# Library logging stays silent unless the embedding application configures it;
# without this the root lastResort handler duplicates warnings the CLI already prints.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "2.0.0"
__author__ = "Security Research Framework"
__license__ = "MIT"

from hackingtool.core.config import Config

__all__ = ["Config", "__version__"]
