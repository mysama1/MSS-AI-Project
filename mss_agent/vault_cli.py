"""mss-vault CLI wrapper — 主入口."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mssclaw.core.vault_cli import main
main()
