import json
from pathlib import Path
import matplotlib.pyplot as plt


def load_results(path):
    with open(path) as f:
        data = json.load(f)
    success = [d["success"] for d in data]
    attempts = [d["attempts"] for d in data]
    return success, attempts


def main():
    reasoning_path = Path("results_tool_refine.json")
    tool_only_path = Path("results_toolonly.json")

    reason_success, reason_attempts = load_results(reasoning_path)
    tool_success, tool_attempts = load_results(tool_only_path)

    labels = ["With Refinement", "Tool Only"]
    success_rates = [
        sum(reason_success) / len(reason_success) * 100,
        sum(tool_success) / len(tool_success) * 100,
    ]

    fig, ax = plt.subplots()
    ax.bar(labels, success_rates, color=["skyblue", "salmon"])
    ax.bar(labels, success_rates, color=["skyblue", "salmon"], width=0.5)
    ax.set_ylabel("Success Rate")
    ax.set_ylim(0, 105)
    ax.set_title("Task Success Rate Comparison")
    for i, v in enumerate(success_rates):
        ax.text(i, v + 0.5, f"{v:.2f}%", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig("success_rates.png")

    times_sec = [1581, 1065]  # total runtime in seconds
    avg_times = [79.06, 53.30]  # seconds per task
    fig3, ax3 = plt.subplots()
    bar_locations = range(len(labels))
    ax3.bar(bar_locations, [t / 60 for t in times_sec], width=0.5,
            color=["skyblue", "salmon"])
    ax3.set_xticks(bar_locations)
    ax3.set_xticklabels(labels)
    ax3.set_ylim(0, 30)
    ax3.set_ylabel("Total Runtime (min)")
    ax3.set_title("Evaluation Time Comparison")
    for i, (total, avg) in enumerate(zip(times_sec, avg_times)):
        ax3.text(i, (total / 60) + 0.2,
                 f"{total // 60}:{total % 60:02d}\n({avg:.2f}s/task)",
                 ha="center", va="bottom")
    fig3.tight_layout()
    fig3.savefig("times.png")

    fig2, ax2 = plt.subplots()
    ax2.hist(reason_attempts,
             bins=range(1, max(reason_attempts) + 2),
             align="left",
             rwidth=0.8)
    ax2.set_xlabel("Attempts")
    ax2.set_ylabel("Number of Tasks")
    ax2.set_title("Attempts per Task (With Reasoning)")
    fig2.tight_layout()
    fig2.savefig("attempts_distribution.png")


if __name__ == "__main__":
    main()
    