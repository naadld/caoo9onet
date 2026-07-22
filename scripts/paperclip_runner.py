#!/usr/bin/env python3
"""
Paperclip AI Agent Pipeline Orchestrator for O9O.NET.
Provides automated triggers for Paperclip AI agent sessions.
Can run individual steps or the full decoupled loop without blocking.
Includes automated anti-duplicate checks and garbage cleanup agent.
"""

import os
import sys
import subprocess
import argparse

BASE_DIR = "/media/vpsg24gb/DATA1/o9o"
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

def run_step(step_name, args=None):
script_map = {
"step1": os.path.join(SCRIPTS_DIR, "step1_direct_stream.py"),
"step2": os.path.join(SCRIPTS_DIR, "step2_link_database.py"),
"step3": os.path.join(SCRIPTS_DIR, "step3_git_publish.py"),
"cleanup": os.path.join(SCRIPTS_DIR, "cleanup_garbage.py"),
}

script_path = script_map.get(step_name)
if not script_path or not os.path.exists(script_path):
print(f"❌ Unknown or missing step: {step_name}")
return False

cmd = ["python3", script_path] + (args or [])
print(f"\n⚡ Paperclip AI Triggering [{step_name.upper()}]: {' '.join(cmd)}")
res = subprocess.run(cmd, cwd=BASE_DIR)
return res.returncode == 0

def main():
parser = argparse.ArgumentParser(description="Paperclip AI Pipeline Orchestrator for O9O.NET")
parser.add_argument("--step", choices=["step1", "step2", "step3", "cleanup", "all"], default="all", help="Pipeline step to run")
parser.add_argument("--max-days", type=int, default=1, help="Max days to process per run in step1")

args = parser.parse_args()

if args.step == "all":
print("🤖 Running full decoupled pipeline loop with Cleanup Agent...")
run_step("step1", ["--max-days", str(args.max_days)])
run_step("step2")
run_step("step3")
run_step("cleanup")
else:
extra_args = ["--max-days", str(args.max_days)] if args.step == "step1" else []
run_step(args.step, extra_args)

if __name__ == "__main__":
main()
