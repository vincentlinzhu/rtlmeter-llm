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
    lambda s: drop_first(";", s),
    lambda s: drop_first(")", s),
    lambda s: flip_first("==", "!=", s),
    lambda s: flip_first("&&", "||", s),
    lambda s: flip_first("<",  ">",  s),
    lambda s: flip_first("1'b0", "1'b1", s),
    lambda s: flip_first("0", "1", s),
    lambda s: s.replace("posedge", "negedge", 1),
    lambda s: misspell_first("module",   "modul",    s),
    lambda s: misspell_first("endmodule","endmodul", s),
    lambda s: misspell_first("begin",    "begn",     s),
    lambda s: misspell_first("end",      "en",       s),
]

def inject_bug(src: str) -> str:
    applicable = [t for t in BUG_TRANSFORMS if t.__code__.co_consts[1] in src]
    if not applicable:
        return src + "\n// BUG"
    return random.choice(applicable)(src)

# --- new helper to detect includes or imports -------------------------------
import re

def has_imports_or_includes(src: str) -> bool:
    # 1) textual includes
    if re.search(r'`include\b', src):
        return True

    # 2) SV import statements
    if re.search(r'\bimport\b', src):
        return True

    # 3) package declarations
    if re.search(r'\bpackage\s+\w+\s*;', src):
        return True

    # 4) scope-resolution operator (e.g. pkg::symbol)
    if '::' in src:
        return True

    # 5) any macro use (e.g. `ASSERT_INIT)
    if re.search(r'`[A-Za-z_]\w*', src):
        return True

    # 6) parameterized instantiation: Foo #(...) instName (...)
    if re.search(r'\b\w+\s*#\s*\(', src):
        return True

    # 7) unparameterized instantiation: Foo instName (...)
    #    make sure we’re not matching the module header itself
    if re.search(r'^\s*(?!module\b)\w+\s+\w+\s*\(', src, re.MULTILINE):
        return True

    return False



def collect_tasks(design_roots, num_tasks, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    verilog_files = []

    # gather all .v/.sv that do NOT contain imports/includes
    for root in design_roots:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if not (f.endswith(".v") or f.endswith(".sv")):
                    continue
                path = os.path.join(dirpath, f)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    src = fh.read()
                if has_imports_or_includes(src):
                    # skip any file with includes or imports
                    continue
                verilog_files.append(path)

    random.shuffle(verilog_files)
    selected = verilog_files[:num_tasks]

    for idx, vf in enumerate(selected):
        task_name = f"task_{idx:02d}"
        tdir = os.path.join(out_dir, task_name)
        os.makedirs(tdir, exist_ok=True)

        with open(vf) as f:
            src = f.read()
            
        bug_src = inject_bug(src)

        ext = os.path.splitext(vf)[1]  # preserve '.v' or '.sv'
        bug_name  = f"bug{ext}"
        fixed_name = f"fixed{ext}"
        bug_path   = os.path.join(tdir, bug_name)
        fixed_path = os.path.join(tdir, fixed_name)

        with open(bug_path,   "w") as f: f.write(bug_src)
        with open(fixed_path, "w") as f: f.write(src)

        trace_file = os.path.join(tdir, "trace.log")
        try:
            proc = subprocess.run(
                ["verilator", "--lint-only", bug_path],
                capture_output=True, text=True
            )
            out = proc.stdout + proc.stderr
        except FileNotFoundError:
            out = "verilator_not_found\n"

        with open(trace_file, "w") as log:
            log.write(out)

        meta = {"bug_file": bug_name,
                "fixed_file": fixed_name,
                "trace": "trace.log"}
        with open(os.path.join(tdir, "README.yaml"), "w") as f:
            yaml.safe_dump(meta, f)

def main():
    parser = argparse.ArgumentParser(
        description="Generate bug-fixing tasks from Verilog designs"
    )
    parser.add_argument("--design_roots", nargs="+", required=True)
    parser.add_argument("--num_tasks",    type=int, required=True)
    parser.add_argument("--output",       required=True)
    args = parser.parse_args()
    collect_tasks(args.design_roots, args.num_tasks, args.output)

if __name__ == "__main__":
    main()
