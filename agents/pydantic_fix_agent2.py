import argparse
import glob
import json
import os
import subprocess
import tempfile
import threading
import time
from typing import List, Optional

from dotenv import load_dotenv

from openai import OpenAI

client = OpenAI()
import yaml
from pydantic import BaseModel

load_dotenv()


class ProgressTimer:
    """Simple progress timer to show elapsed time during LLM calls."""
    
    def __init__(self):
        self.start_time = None
        self.stop_event = None
        self.thread = None
        
    def start(self, message="LLM processing"):
        """Start the progress timer."""
        self.start_time = time.time()
        self.stop_event = threading.Event()
        
        def show_progress():
            while not self.stop_event.is_set():
                elapsed = time.time() - self.start_time
                print(f"\r{message}... {elapsed:.1f}s", end="", flush=True)
                time.sleep(0.5)
        
        self.thread = threading.Thread(target=show_progress, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the progress timer."""
        if self.stop_event:
            self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"\rCompleted in {elapsed:.1f}s" + " " * 20)  # Clear the line
        return elapsed


class OpenAIClient:
    """Lightweight OpenAI ChatCompletion client."""

    def __init__(self, model: str) -> None:
        self.model = model

    def chat(self, messages: List[dict], tools: Optional[List[dict]] = None):
        return client.chat.completions.create(model=self.model,
        messages=messages,
        tools=tools,
        tool_choice="auto" if tools else None)


def run_verilator_tool(code: str) -> str:
    """Helper used by the OpenAI tool call."""
    with tempfile.NamedTemporaryFile(suffix=".v", delete=False) as tmp:
        tmp.write(code.encode())
        tmp_path = tmp.name
    success, stderr = run_verilator(tmp_path)
    os.remove(tmp_path)
    return json.dumps({"success": success, "stderr": stderr})


def apply_patch_tool(original_code: str, fixed_code: str) -> str:
    """Tool function to apply the patch by returning the fixed code."""
    return json.dumps({"fixed_code": fixed_code, "applied": True})


def call_llm(client: OpenAIClient, system: str, prompt: str, original_code: str) -> tuple[str, bool]:
    """Call OpenAI with tool usage for both verification and patching."""
    timer = ProgressTimer()
    
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
        },
        {
            "type": "function",
            "function": {
                "name": "apply_patch",
                "description": "Apply the fix by providing the complete corrected Verilog code",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fixed_code": {
                            "type": "string",
                            "description": "The complete corrected Verilog code"
                        }
                    },
                    "required": ["fixed_code"],
                },
            },
        }
    ]

    timer.start("Calling LLM for initial analysis")
    try:
        resp = client.chat(messages, tools=tools)
    finally:
        timer.stop()
        
    message = resp.choices[0].message

    fixed_code = None
    tool_used = False
    tool_call_count = 0

    # Handle tool calls in a loop until no more tool calls
    while hasattr(message, "tool_calls") and message.tool_calls:
        messages.append({
            "role": "assistant", 
            "content": message.content,
            "tool_calls": message.tool_calls
        })
        
        for call in message.tool_calls:
            tool_call_count += 1
            
            if call.function.name == "run_verilator":
                print(f"Tool call {tool_call_count}: Running Verilator verification...")
                timer.start("Running Verilator")
                try:
                    args = json.loads(call.function.arguments)
                    output = run_verilator_tool(args["code"])
                finally:
                    timer.stop()
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": "run_verilator",
                    "content": output,
                })
                tool_used = True
                
            elif call.function.name == "apply_patch":
                print(f"Tool call {tool_call_count}: Applying patch...")
                args = json.loads(call.function.arguments)
                fixed_code = args["fixed_code"]
                output = apply_patch_tool(original_code, fixed_code)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": "apply_patch", 
                    "content": output,
                })
                tool_used = True
        
        # Get next response if there were tool calls
        if tool_call_count > 0:
            timer.start("LLM processing tool results")
            try:
                resp = client.chat(messages, tools=tools)
            finally:
                timer.stop()
            message = resp.choices[0].message

    # If no patch tool was called, try to extract code from the response
    if fixed_code is None and message.content:
        print("No patch tool used, attempting to extract code from response...")
        # Fallback: try to extract code from the response
        content = message.content.strip()
        # Look for code blocks or assume the entire response is code
        if "```" in content:
            # Extract from code block
            import re
            code_match = re.search(r'```(?:verilog|v)?\n(.*?)\n```', content, re.DOTALL)
            if code_match:
                fixed_code = code_match.group(1)
        else:
            # Assume entire response is code if it looks like Verilog
            if any(keyword in content.lower() for keyword in ['module', 'endmodule', 'always', 'assign']):
                fixed_code = content

    return fixed_code or original_code, tool_used


def run_verilator(src_path: str) -> tuple[bool, str]:
    proc = subprocess.run(["verilator", "--lint-only", src_path], capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr


def solve_task(
    task_yaml: str,
    save_dir: Optional[str] = "history/",
    self_refine: bool = True,
    max_rounds: int = 5,
    client: Optional[OpenAIClient] = None,
) -> dict:
    task_dir = os.path.dirname(task_yaml)
    with open(task_yaml) as f:
        meta = yaml.safe_load(f)
    bug_file = meta.get("bug_file")
    if bug_file is None:
        for candidate in ["bug.v", "bug.sv"]:
            if os.path.exists(os.path.join(task_dir, candidate)):
                bug_file = candidate
                break
        else:
            bug_file = "bug.v"
    bug_file = os.path.join(task_dir, bug_file)
    trace_file = os.path.join(task_dir, meta.get("trace", "trace.log"))
    with open(bug_file) as f:
        original_src = f.read()
    with open(trace_file) as f:
        original_trace = f.read()

    system_prompt = """You are a seasoned Verilog engineer. Given a failing design and a compiler trace, fix the bug in the code.

You have access to two tools:
1. run_verilator: Test Verilog code for syntax/lint errors
2. apply_patch: Provide the complete corrected Verilog code

Your workflow should be:
1. Analyze the buggy code and error trace
2. Optionally use run_verilator to test your understanding
3. Use apply_patch to provide the complete fixed code

Focus on providing clean, working Verilog code that addresses all the issues in the trace."""

    if client is None:
        raise ValueError("OpenAI client must be provided with a model name")

    history = []
    current_src = original_src
    current_trace = original_trace
    
    for round_idx in range(1, max_rounds + 1):
        print(f"\n=== Round {round_idx}/{max_rounds} ===")
        user_prompt = f"BUGGY FILE:\n{current_src}\n\nTRACE:\n{current_trace}\n"
        
        if round_idx > 1:
            user_prompt += f"\nPREVIOUS ATTEMPTS:\n"
            for i, h in enumerate(history, 1):
                user_prompt += f"Attempt {i}: {'SUCCESS' if h['success'] else 'FAILED'}\n"
                if not h['success'] and 'stderr' in h:
                    user_prompt += f"Error: {h['stderr']}\n"
            user_prompt += f"\nThe above attempts failed. Please fix ALL the issues shown in the traces.\n"
            
        try:
            new_src, tool_used = call_llm(client, system_prompt, user_prompt, current_src)
            
            # Test the fixed code
            print("Testing fixed code with Verilator...")
            with tempfile.NamedTemporaryFile(suffix=".v", delete=False) as tmp:
                tmp.write(new_src.encode())
                tmp_path = tmp.name
            success, stderr = run_verilator(tmp_path)
            os.remove(tmp_path)
            
        except Exception as e:
            success = False
            stderr = f"Exception during LLM call: {str(e)}"
            new_src = current_src
            
        # Store the attempt with stderr information
        attempt_record = {
            "round": round_idx, 
            "prompt": user_prompt, 
            "response": new_src, 
            "success": success,
            "stderr": stderr,
            "tool_used": tool_used if 'tool_used' in locals() else False
        }
        history.append(attempt_record)
        
        if success:
            print(f"✅ Success on round {round_idx}!")
            break
        else:
            print(f"❌ Round {round_idx} failed with errors:")
            print(stderr)
            
            if self_refine:
                # Update src and trace for next iteration
                current_src = new_src
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
    
    print("FINAL CODE:")
    print(new_src)
    
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