#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from typing import Dict

def find_fixed_file(task_dir: str):
    """Return full path to fixed.v or fixed.sv in task_dir, or None if neither exists."""
    for ext in (".sv", ".v"):
        path = os.path.join(task_dir, f"fixed{ext}")
        if os.path.isfile(path):
            return path
    return None

def lint_file(verilator_cmd: str, file_path: str) -> Dict:
    """Run verilator --lint-only on file_path. Return dict with returncode, stdout, stderr."""
    proc = subprocess.run(
        [verilator_cmd, "--lint-only", file_path],
        capture_output=True,
        text=True
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }

def main():
    parser = argparse.ArgumentParser(
        description="Sanity‐check all fixed.v/.sv files in task subdirectories with verilator."
    )
    parser.add_argument(
        "tasks_dir",
        help="Path to your root 'tasks' directory (containing task_00/, task_01/, ...)"
    )
    parser.add_argument(
        "--verilator",
        default="verilator",
        help="Path to the verilator executable (default: verilator)"
    )
    args = parser.parse_args()

    if not os.path.isdir(args.tasks_dir):
        print(f"ERROR: {args.tasks_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    results = {}
    # look for immediate subdirectories named task_*
    for entry in sorted(os.listdir(args.tasks_dir)):
        task_path = os.path.join(args.tasks_dir, entry)
        if not os.path.isdir(task_path):
            continue
        fixed = find_fixed_file(task_path)
        if not fixed:
            results[entry] = {"status": "no_fixed", "detail": "no fixed.v or fixed.sv found"}
            continue

        res = lint_file(args.verilator, fixed)
        if res["returncode"] == 0:
            results[entry] = {"status": "pass"}
        else:
            # capture first few lines of stderr for brevity
            err_summary = "\n".join(res["stderr"].splitlines()[:5])
            results[entry] = {"status": "fail", "detail": err_summary}

    # print a table-like summary
    print(f"{'TASK':<12} {'RESULT':<6}  DETAILS")
    print("-" * 50)
    passed = failed = skipped = 0
    for task, info in results.items():
        status = info["status"]
        if status == "pass":
            passed += 1
            detail = ""
        elif status == "fail":
            failed += 1
            detail = info["detail"]
        else:
            skipped += 1
            detail = info["detail"]
        print(f"{task:<12} {status:<6}  {detail}")

    print("\nSummary:")
    print(f"  Passed : {passed}")
    print(f"  Failed : {failed}")
    print(f"  Skipped: {skipped}")

if __name__ == "__main__":
    main()
