import argparse
import glob
import json
import os
import subprocess
import tempfile
from typing import List, Optional

from dotenv import load_dotenv

from openai import OpenAI

client = OpenAI()
import yaml
from pydantic import BaseModel

load_dotenv()


class OpenAIClient:
    """Lightweight OpenAI ChatCompletion client."""

    def __init__(self, model: str = "gpt-3.5-turbo") -> None:
        self.model = model

    def chat(self, messages: List[dict], tools: Optional[List[dict]] = None):
        return client.chat.completions.create(model=self.model,
        messages=messages,
        tools=tools,
        tool_choice="auto" if tools else None)


class PatchResponse(BaseModel):
    """Schema for LLM patch response."""

    diff: str


def run_verilator_tool(code: str) -> str:
    """Helper used by the OpenAI tool call."""
    with tempfile.NamedTemporaryFile(suffix=".v", delete=False) as tmp:
        tmp.write(code.encode())
        tmp_path = tmp.name
    success = run_verilator(tmp_path)
    os.remove(tmp_path)
    return json.dumps({"success": success})


def call_llm(client: OpenAIClient, system: str, prompt: str) -> str:
    """Call OpenAI with optional tool usage."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_verilator",
                "description": "Run verilator lint on provided Verilog code",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            },
        }
    ]

    resp = client.chat(messages, tools=tools)
    message = resp.choices[0].message

    # handle tool calls in a single round
    if hasattr(message, "tool_calls") and message.tool_calls:
        for call in message.tool_calls:
            if call.function.name == "run_verilator":
                args = json.loads(call.function.arguments)
                output = run_verilator_tool(args["code"])
                messages.append({"role": "assistant", "content": None, "tool_calls": [call]})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": "run_verilator",
                        "content": output,
                    }
                )
        resp = client.chat(messages)
        message = resp.choices[0].message

    return message.content.strip()


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


def solve_task(
    task_yaml: str,
    save_dir: Optional[str] = None,
    self_refine: bool = True,
    max_rounds: int = 3,
    client: Optional[OpenAIClient] = None,
) -> dict:
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

    if client is None:
        client = OpenAIClient()

    history = []
    for round_idx in range(1, max_rounds + 1):
        user_prompt = f"BUGGY FILE:\n{src}\n\nTRACE:\n{trace}\n"
        llm_out = call_llm(client, system_prompt, user_prompt)
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
    client = OpenAIClient(model="gpt-4o-mini")
    for task in sorted(glob.glob(args.task_glob)):
        result = solve_task(task, save_dir=args.save, self_refine=not args.no_self_refine, client=client)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
