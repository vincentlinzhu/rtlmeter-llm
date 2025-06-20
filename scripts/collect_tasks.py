import argparse
import os
import random
import subprocess
import yaml
import re

# --- new helper transforms --------------------------------------------------
def drop_first(char: str, src: str) -> str:
    """Remove the first occurrence of *char* (useful for ';', ')', ']' …)."""
    return src.replace(char, "", 1)

def flip_first(a: str, b: str, src: str) -> str:
    """Swap operator *a* for *b* (e.g. '==' -> '!=', '&&' -> '||')."""
    return src.replace(a, b, 1)

def misspell_first(word: str, wrong: str, src: str) -> str:
    """Change the first exact keyword *word* to the faulty spelling *wrong*."""
    return re.sub(rf"\b{word}\b", wrong, src, count=1)

# --- master list of possible bug generators ---------------------------------
BUG_TRANSFORMS = [
    #  syntax deletions
    lambda s: drop_first(";", s),                     # remove semicolon
    lambda s: drop_first(")", s),                     # drop closing paren
    #  operator flips
    lambda s: flip_first("==", "!=", s),
    lambda s: flip_first("&&", "||", s),
    lambda s: flip_first("<",  ">",  s),
    #  literal tweaks
    lambda s: flip_first("1'b0", "1'b1", s),
    lambda s: flip_first("0", "1", s),                # first decimal 0 → 1
    #  clock-edge reversal
    lambda s: s.replace("posedge", "negedge", 1),
    #  keyword misspellings
    lambda s: misspell_first("module",   "modul",    s),
    lambda s: misspell_first("endmodule","endmodul", s),
    lambda s: misspell_first("begin",    "begn",     s),
    lambda s: misspell_first("end",      "en",       s),
]

def inject_bug(src: str) -> str:
    """
    Inject a single random bug into *src*.

    The function scans the candidate transforms above and keeps only those that
    are applicable to the current source (i.e. their trigger string is present).
    One applicable transform is chosen uniformly at random and applied.
    If, for some reason, none match, we append a dummy comment.
    """
    # Figure out which transforms can actually fire on this file
    applicable = [t for t in BUG_TRANSFORMS if t.__code__.co_consts[1] in src]
    if not applicable:          # nothing found? fall back
        return src + "\n// BUG"

    transform = random.choice(applicable)
    return transform(src)


# def inject_bug(src: str) -> str:
#     if ";" in src:
#         return src.replace(";", "", 1)
#     if "==" in src:
#         return src.replace("==", "!=", 1)
#     if "0" in src:
#         return src.replace("0", "1", 1)
#     return src + "\n// BUG"


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
            proc = subprocess.run(["verilator", "--lint-only", bug_path], capture_output=True, text=True)
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
    