import os
import sys

# Make the src/ layout importable even without `pip install -e .`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
