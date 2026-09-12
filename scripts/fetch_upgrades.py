#!/usr/bin/env python3
"""Queue a durable collection job in the canonical API container."""
import subprocess
import sys
raise SystemExit(subprocess.call(["docker","compose","exec","-T","api","python","-m","app.cli","collect",*sys.argv[1:]]))
