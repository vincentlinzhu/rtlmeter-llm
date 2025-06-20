import argparse
import glob
import json
import os
import subprocess
import difflib
import re
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

    def __init__(self, model: str) -> None:
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
    success, stderr = run_verilator(tmp_path)
    os.remove(tmp_path)
    return json.dumps({"success": success, "stderr": stderr})


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

    resp = client.chat(
        messages
        # tools=tools
    )
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


# def apply_patch(src: str, diff: str) -> str:
#     """Apply unified diff patch to the given source."""
#     with tempfile.TemporaryDirectory() as td:
#         src_path = os.path.join(td, "buggy_file.v")
#         with open(src_path, "w") as f:
#             f.write(src)
#         patch_path = os.path.join(td, "patch.diff")
#         with open(patch_path, "w") as f:
#             f.write(diff)
#         res = subprocess.run(["patch", src_path, patch_path], capture_output=True, text=True)
#         if res.returncode == 0:
#             with open(src_path) as f:
#                 return f.read()
#     return src


def apply_patch(src: str, diff: str) -> str:
    """Apply patch using Python's difflib for more reliable parsing."""
    # Parse the unified diff
    lines = diff.strip().split('\n')
    
    # Find the lines that need to be changed
    changes = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('@@'):
            # Parse the hunk header
            match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1
                
                # Collect the changes in this hunk
                i += 1
                old_lines = []
                new_lines = []
                
                while i < len(lines) and not lines[i].startswith('@@'):
                    if lines[i].startswith('-'):
                        old_lines.append(lines[i][1:])
                    elif lines[i].startswith('+'):
                        new_lines.append(lines[i][1:])
                    elif lines[i].startswith(' '):
                        # Context line - add to both
                        old_lines.append(lines[i][1:])
                        new_lines.append(lines[i][1:])
                    i += 1
                
                changes.append((old_start - 1, old_lines, new_lines))  # Convert to 0-based indexing
            else:
                i += 1
        else:
            i += 1
    
    # Apply the changes
    src_lines = src.split('\n')
    
    # Apply changes in reverse order to avoid index shifting issues
    for start_idx, old_lines, new_lines in reversed(changes):
        # Replace the old lines with new lines
        end_idx = start_idx + len(old_lines)
        src_lines[start_idx:end_idx] = new_lines
    
    return '\n'.join(src_lines)


def run_verilator(src_path: str) -> bool:
    proc = subprocess.run(["verilator", "--lint-only", src_path], capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr


def solve_task(
    task_yaml: str,
    save_dir: Optional[str] = "/history",
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
        original_trace = f.read()

    system_prompt = system_prompt = """You are a seasoned Verilog engineer. Given a failing design and a compiler trace, return a unified diff patch fixing the bug. Respond in JSON with field 'diff'. The diff should be in unified diff format like:
    @@ -10,1 +10,1 @@
    -old line
    +new line

    Respond *only* with the JSON object, no markdown``` blocks."""

    if client is None:
        raise ValueError("OpenAI client must be provided with a model name")

    history = []
    current_trace = original_trace
    
    for round_idx in range(1, max_rounds + 1):
        # Build the user prompt with current trace (includes new errors from previous attempts)
        user_prompt = f"BUGGY FILE:\n{src}\n\nTRACE:\n{current_trace}\n"
        
        # Add context from previous attempts if this isn't the first round
        if round_idx > 1:
            user_prompt += f"\nPREVIOUS ATTEMPTS:\n"
            for i, h in enumerate(history, 1):
                user_prompt += f"Attempt {i}: {'SUCCESS' if h['success'] else 'FAILED'}\n"
                if not h['success'] and 'stderr' in h:
                    user_prompt += f"Error: {h['stderr']}\n"
            user_prompt += f"\nThe above attempts failed. Please fix ALL the issues shown in the traces.\n"
        
        try:
            # For testing, using your hardcoded response, but in real usage this would be:
            # llm_out = call_llm(client, system_prompt, user_prompt)
            
            # llm_out = json.dumps({"diff":"--- buggy_file.v\n+++ fixed_file.v\n@@ -1,6 +1,6 @@\n // Copyright lowRISC contributors (OpenTitan project).\n // Licensed under the Apache License, Version 2.0, see LICENSE for details.\n // SPDX-License-Identifier: Apache-2.0\n //\n-package pwrmgr_reg_pkg\n+package pwrmgr_reg_pkg;\n \n   // Param list\n   parameter int NumWkups = 6;\n"})
            llm_out = call_llm(client, system_prompt, user_prompt)
            data = json.loads(llm_out)

            # if diff came back as a list, join it into a single string
            if isinstance(data.get("diff"), list):
                data["diff"] = "\n".join(data["diff"])

            # now validate
            patch = PatchResponse(**data)
            # patch = PatchResponse.model_validate_json(llm_out)
        except Exception:
            patch = PatchResponse(diff=llm_out)
        
        # Apply the patch
        new_src = apply_patch(src, patch.diff)
        
        # Test the patched code
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False) as tmp:
            tmp.write(new_src.encode())
            tmp_path = tmp.name
        
        success, stderr = run_verilator(tmp_path)
        os.remove(tmp_path)
        
        # Store the attempt with stderr information
        attempt_record = {
            "round": round_idx, 
            "prompt": user_prompt, 
            "response": llm_out, 
            "success": success,
            "stderr": stderr
        }
        history.append(attempt_record)
        
        if success:
            print(f"Success on round {round_idx}")
            break
        else:
            print(f"Round {round_idx} failed with errors:")
            print(stderr)
            
            if self_refine:
                # Update src and trace for next iteration
                src = new_src
                current_trace = stderr  # Use the new error as the trace for next round
            else:
                break
    
    # Save the history
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        base = os.path.join(save_dir, os.path.basename(task_dir) + ".jsonl")
        with open(base, "w") as f:
            for h in history:
                f.write(json.dumps(h) + "\n")
    
    return {
        "task": os.path.basename(task_dir), 
        "success": history[-1]["success"], 
        "attempts": len(history),
        "final_stderr": history[-1]["stderr"] if not history[-1]["success"] else ""
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run patch generation agent on tasks")
    parser.add_argument("--task_glob", required=True)
    parser.add_argument("--save", default=None, help="Directory to save trajectories")
    parser.add_argument("--no_self_refine", action="store_true")
    parser.add_argument("--model", required=True, help="OpenAI model name")
    args = parser.parse_args()
    client = OpenAIClient(model=args.model)
    for task in sorted(glob.glob(args.task_glob)):
        result = solve_task(task, save_dir=args.save, self_refine=not args.no_self_refine, client=client)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
