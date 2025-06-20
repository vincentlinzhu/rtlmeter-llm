import argparse
import glob
import importlib.util
import json
from pathlib import Path
from tqdm import tqdm

from dotenv import load_dotenv


def load_agent(agent_path: str):
    spec = importlib.util.spec_from_file_location("agent", agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Evaluate agent on tasks")
    parser.add_argument("--agent", required=True, help="Path to agent python file")
    parser.add_argument("--tasks", required=True, help="Directory of tasks")
    parser.add_argument("--out", required=True)
    parser.add_argument("--no_self_refine", action="store_true")
    parser.add_argument("--model", required=True, help="OpenAI model name")
    args = parser.parse_args()

    agent = load_agent(args.agent)
    task_paths = sorted(glob.glob(str(Path(args.tasks) / "*" / "README.yaml")))

    results = []
    for tp in tqdm(task_paths, desc="Solving tasks", unit="task"):
        client = agent.OpenAIClient(model=args.model)
        res = agent.solve_task(tp, self_refine=not args.no_self_refine, client=client)
        results.append(res)
        print(json.dumps(res))

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    success_rate = sum(r["success"] for r in results) / len(results) if results else 0.0
    print(f"Success rate: {success_rate:.2%}")


if __name__ == "__main__":
    main()