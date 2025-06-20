import argparse
import glob
import importlib.util
import json
from pathlib import Path
from tqdm import tqdm
from statistics import mean
import time

from dotenv import load_dotenv


def load_agent(agent_path: str):
    spec = importlib.util.spec_from_file_location("agent", agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Evaluate agent on tasks")
    parser.add_argument("--agent", help="Path to agent python file")
    parser.add_argument("--tasks", help="Directory of tasks")
    parser.add_argument("--out", help="Results JSON file")
    parser.add_argument("--save", default=None, help="Directory to save trajectories")
    parser.add_argument("--no_self_refine", action="store_true")
    parser.add_argument("--no_verilator_tool", action="store_true", help="Disable the run_verilator tool ablation")
    parser.add_argument("--model", help="OpenAI model name")
    parser.add_argument("--config", help="Optional JSON config file with arguments")
    args = parser.parse_args()
    
    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        for k, v in cfg.items():
            setattr(args, k, v)

    if not args.agent or not args.tasks or not args.out or not args.model:
        parser.error("--agent, --tasks, --out and --model must be specified (either via CLI or config)")


    agent = load_agent(args.agent)
    task_paths = sorted(glob.glob(str(Path(args.tasks) / "*" / "README.yaml")))

    results = []
    task_times = []
    for tp in tqdm(task_paths, desc="Solving tasks", unit="task"):
        client = agent.OpenAIClient(model=args.model)
        start = time.time()
        res = agent.solve_task(
            tp,
            save_dir=args.save,
            self_refine=not args.no_self_refine,
            client=client,
            skip_verilator=args.no_verilator_tool,
        )
        elapsed = time.time() - start
        res["time_s"] = elapsed
        task_times.append(elapsed)
        results.append(res)
        print(json.dumps(res))
        
    avg_time = mean(task_times) if task_times else 0.0

    output = {
        "model": args.model,
        "no_self_refine": args.no_self_refine,
        "no_verilator_tool": args.no_verilator_tool,
        "average_time_s": avg_time,
        "results": results,
    }

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)

    success_rate = sum(r["success"] for r in results) / len(results) if results else 0.0
    print(f"Success rate: {success_rate:.2%}")
    print(f"Average time per task: {avg_time:.1f}s")


if __name__ == "__main__":
    main()