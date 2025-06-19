import argparse
import glob
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Optional

import openai
import yaml
from pydantic import BaseModel


class PatchResponse(BaseModel):
    """Schema for LLM patch response."""

    diff: str


def call_llm(system: str, prompt: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    try:
        resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        return resp.choices[0].message["content"].strip()
    except Exception as exc:
        return f"LLM_ERROR: {exc}"


def apply_patch(src: str, diff: str) -> str:
    """Apply unified diff patch to the given source."""
    with tempfile.TemporaryDirectory() as td:
        src_path = os.path.join(td, "bug.v")
        with open(src_path, "w") as f:
            f.write(src)
        patch_path = os.path.join(td, "patch.diff")
        with open(patch_path, "w") as f:
            f.write(diff)
        res = subprocess.run(["patch", src_path, patch_path], capture_output=True, text=True)
        if res.returncode == 0:
            with open(src_path) as f:
                return f.read()
    return src


def run_verilator(src_path: str) -> bool:
    proc = subprocess.run(["verilator", "--lint-only", src_path], capture_output=True, text=True)
    return proc.returncode == 0


def solve_task(task_yaml: str, save_dir: Optional[str] = None, self_refine: bool = True, max_rounds: int = 3) -> dict:
    task_dir = os.path.dirname(task_yaml)
    with open(task_yaml) as f:
        meta = yaml.safe_load(f)
    bug_file = os.path.join(task_dir, meta.get("bug_file", "bug.v"))
    trace_file = os.path.join(task_dir, meta.get("trace", "trace.log"))
    with open(bug_file) as f:
        src = f.read()
    with open(trace_file) as f:
        trace = f.read()

    system_prompt = "You are a seasoned Verilog engineer. Given a failing design and a compiler trace, return a unified diff patch fixing the bug. Respond in JSON with field 'diff'."

    history = []
    for round_idx in range(1, max_rounds + 1):
        user_prompt = f"BUGGY FILE:\n{src}\n\nTRACE:\n{trace}\n"
        llm_out = call_llm(system_prompt, user_prompt)
        try:
            patch = PatchResponse.model_validate_json(llm_out)
        except Exception:
            patch = PatchResponse(diff=llm_out)
        new_src = apply_patch(src, patch.diff)
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False) as tmp:
            tmp.write(new_src.encode())
            tmp_path = tmp.name
        success = run_verilator(tmp_path)
        os.remove(tmp_path)
        history.append({"round": round_idx, "prompt": user_prompt, "response": llm_out, "success": success})
        if success or not self_refine:
            break
        src = new_src
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        base = os.path.join(save_dir, os.path.basename(task_dir) + ".jsonl")
        with open(base, "w") as f:
            for h in history:
                f.write(json.dumps(h) + "\n")
    return {"task": os.path.basename(task_dir), "success": history[-1]["success"], "attempts": len(history)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run patch generation agent on tasks")
    parser.add_argument("--task_glob", required=True)
    parser.add_argument("--save", default=None, help="Directory to save trajectories")
    parser.add_argument("--no_self_refine", action="store_true")
    args = parser.parse_args()
    for task in sorted(glob.glob(args.task_glob)):
        result = solve_task(task, save_dir=args.save, self_refine=not args.no_self_refine)
        print(json.dumps(result))


if __name__ == "__main__":
    main()