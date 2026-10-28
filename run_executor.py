"""Launch the independent executor (defaults to monitoring until owner arms it)."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'backend'))
from qros.services.executor import main
if __name__=='__main__':main()
