import argparse
import os
import random
import subprocess
import yaml


def inject_bug(src: str) -> str:
    if "==" in src:
        return src.replace("==", "!=", 1)
    if "0" in src:
        return src.replace("0", "1", 1)
    return src + "\n// BUG"


def collect_tasks(design_roots, num_tasks, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    verilog_files = []
    for root in design_roots:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".v") or f.endswith(".sv"):
                    verilog_files.append(os.path.join(dirpath, f))
    random.shuffle(verilog_files)
    selected = verilog_files[:num_tasks]

    for idx, vf in enumerate(selected):
        task_name = f"task_{idx:02d}"
        tdir = os.path.join(out_dir, task_name)
        os.makedirs(tdir, exist_ok=True)
        with open(vf) as f:
            src = f.read()
        bug_src = inject_bug(src)
        bug_path = os.path.join(tdir, "bug.v")
        fixed_path = os.path.join(tdir, "fixed.v")
        with open(bug_path, "w") as f:
            f.write(bug_src)
        with open(fixed_path, "w") as f:
            f.write(src)
        trace_file = os.path.join(tdir, "trace.log")
        try:
            verilator_cmd = ["verilator", "--lint-only", bug_path]
            for root in design_roots:
                verilator_cmd += ["-y", root, "-I", root]
            proc = subprocess.run(verilator_cmd, capture_output=True, text=True)
            with open(trace_file, "w") as log:
                log.write(proc.stdout + proc.stderr)
        except FileNotFoundError:
            with open(trace_file, "w") as log:
                log.write("verilator_not_found\n")
        meta = {"bug_file": "bug.v", "fixed_file": "fixed.v", "trace": "trace.log"}
        with open(os.path.join(tdir, "README.yaml"), "w") as f:
            yaml.safe_dump(meta, f)


def main():
    parser = argparse.ArgumentParser(description="Generate bug-fixing tasks from Verilog designs")
    parser.add_argument("--design_roots", nargs="+", required=True)
    parser.add_argument("--num_tasks", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    collect_tasks(args.design_roots, args.num_tasks, args.output)


if __name__ == "__main__":
    main()
    