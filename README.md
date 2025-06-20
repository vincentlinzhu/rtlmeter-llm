# rtlmeter-llm

Follow the copy‑paste‑ready commands below; they assume a fresh VM with sudo access.

---

## 0  TL;DR (10‑line Quick‑Start — Ubuntu 24.04)

```bash
# 1. Clone repos
git clone git@github.com:vincentlinzhu/rtlmeter-llm.git
cd rtlmeter-llm
git clone https://github.com/verilator/verilator.git
git clone https://github.com/verilator/rtlmeter.git

# 2. System deps — Ubuntu 24.04 (≈30 s)
sudo apt update && sudo apt install -y git make autoconf g++ flex bison \
  libfl2 libfl-dev zlib1g zlib1g-dev python3-venv build-essential help2man

# 3. Build & install Verilator (≈2‑3 min on 8‑vCPU t3.xlarge)
cd verilator && git checkout stable && autoconf && ./configure && \
  make -j$(nproc) && sudo make install && cd ..

# 4. Python env + RTLMeter deps
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -r rtlmeter/requirements.txt openai langchain[all] pandas jinja2 rich

```

---

## 1  Prerequisites

| Tool               | Version tested (June 2025)         | Install notes                           |
| ------------------ | ---------------------------------- | --------------------------------------- |
| **Python**         | ≥ 3.10 (Ubuntu ships 3.12)         | `sudo apt install python3 python3-venv` |
| **GCC / Clang**    | ≥ 13 (Ubuntu 24.04 default GCC‑14) | part of `build-essential`               |
| **Git**            | latest                             | `sudo apt install git`                  |
| **Verilator**      | 5.026‑dev (`stable` tag)           | built from source (§2.2)                |
| **RTLMeter**       | `master` (June 2025)               | cloned from GitHub                      |
| **OpenAI API key** | env var `OPENAI_API_KEY`           | required for agent evaluation           |

---

## 2  Environment Setup (Ubuntu 24.04)

### 2.1 System packages

```bash
sudo apt update && sudo apt install -y git make autoconf g++ flex bison \
  libfl2 libfl-dev zlib1g zlib1g-dev python3-venv build-essential
```

> **Tip** Ubuntu 24.04 ships GCC‑14; Verilator compiles cleanly. If you prefer Clang:
> `sudo apt install clang` and add `CXX=clang++` before `./configure`.

### 2.2 Build & install Verilator from Git

```bash
cd verilator
# Pin to known‑good commit (optional)
git checkout stable   # tracks latest release‑ready commit

# Generate configure script & build
autoconf && ./configure && make -j$(nproc)

# Install to /usr/local (requires sudo)
sudo make install

# Verify
which verilator && verilator --version
cd ..
```

### 2.3 Python virtual environment & RTLMeter

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r rtlmeter/requirements.txt
```

*(adds pyverilator, pytest, etc.  You’ll install LLM deps in §3.)*

### 2.4 Sanity‑check installation

```bash
cd rtlmeter
./rtlmeter run --cases OpenTitan:default:hello
./rtlmeter report
```

Expect:
```bash 
@@@ (1/6) OpenTitan:default - Prepare files for compilation
@@@ === Skipping due to success on earlier run ===
@@@ (2/6) OpenTitan:default - Verilate
@@@ === Skipping due to success on earlier run ===
@@@ (3/6) OpenTitan:default - Build C++
@@@ === Skipping due to success on earlier run ===
@@@ (4/6) OpenTitan:default:hello - Prepare files for execution
@@@ === Skipping due to success on earlier run ===
@@@ (5/6) OpenTitan:default:hello - Execute simulation
@@@ === Skipping due to success on earlier run ===
@@@ (6/6) OpenTitan:default:hello - Post hook
@@@ === Skipping due to success on earlier run ===
@@@ All cases passed

verilate
╒═══════════════════╤═══╤══════════════════╤═══════════════════╕
│ Case              │ # │ Elapsed time [s] │  Peak memory [MB] │
╞═══════════════════╪═══╪══════════════════╪═══════════════════╡
│ OpenTitan:default │ 1 │  70.65           │ 1918.97           │
╞═══════════════════╪═══╪══════════════════╪═══════════════════╡
│ All               │   │  70.65           │ 1918.97           │
╘═══════════════════╧═══╧══════════════════╧═══════════════════╛

execute
╒═════════════════════════╤═══╤═════════════════╤══════════════════╤══════════════════╕
│ Case                    │ # │ Sim speed [kHz] │ Elapsed time [s] │ Peak memory [MB] │
╞═════════════════════════╪═══╪═════════════════╪══════════════════╪══════════════════╡
│ OpenTitan:default:hello │ 1 │  3.61           │  28.44           │  23.68           │
╞═════════════════════════╪═══╪═════════════════╪══════════════════╪══════════════════╡
│ All                     │   │                 │  28.44           │  23.68           │
╘═════════════════════════╧═══╧═════════════════╧══════════════════╧══════════════════╛
```

---

## 3  Benchmark Creation (Part 1)

| Candidate task                                                                                          | Pros                                                                                                                                                                                                                                                            | Cons / hidden cost                                                                        |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **A. Trace-to-Code Bug Fixing** (feed a failing Verilator trace + buggy Verilog; model outputs a patch) | \* Binary success metric\* (design passes after patch) — easy scoring<br>\* Small diff size → compact prompts and responses<br>\* You can script dataset creation: randomly mutate one line, re-run RTLMeter until it fails, store the failing trace + bug file | Needs a robust mutation script to guarantee “single-edit” bugs                            |
| B. **Specification → Code Synthesis** (generate an entire module from natural-language spec)            | Flashy; shows LLM creativity                                                                                                                                                                                                                                    | Hard to grade automatically (need formal spec or hand-written tests for each of 20 cases) |
| C. **Testbench Generation** (given RTL, generate a test that hits coverage)                             | Good for hardware focus                                                                                                                                                                                                                                         | Requires coverage tooling (gcc + Verilator coverage, LCOV parsing, etc.) — more infra     |
| D. **Bug-Localization Only** (identify line/region of bug, no patch)                                    | Easy patches not required                                                                                                                                                                                                                                       | Less impressive; still needs ground-truth labels                                          |
| E. **Lint-Fix or Style-Fix** (convert non-compliant code to standard style)                             | Simple pass/fail via lint tool                                                                                                                                                                                                                                  | Lower technical depth; easier to “cheat” with regex models                                |



Why it fits this take-home:

1. Scorable with a single command. After the model proposes a patch you just run

```bash
verilator --cc ... && c++ && ./sim
or RTLMeter. Pass = 1, fail = 0 — easy leaderboard.
```

2. Dataset can be auto-generated. A 50-line Python script can:

    - pick a clean design,

    - mutate one ==→!=, +→-, flip a wire width, etc.,

    - save the failing trace & diff only if the original still passed.

3. 20 cases is realistic. Each compile-and-sim loop is < 1 min with small designs (picorv32, amber23).

4. Uses the user’s Verilog + debugging skills. Aligns with what the company cares about (hardware tool flow) and shows LLM+tool orchestration.

5. Room for agent creativity. You can baseline with a simple “single-edit-search” agent, then show ablations (self-refine, error-chain-of-thought).


PART 1 Explanation:
1. **Define the Task** — *Trace‑to‑Code Bug‑Fixing*.
  
    Concrete Definition:

    | Field       | Value                                                                                                                       |
    | ----------- | --------------------------------------------------------------------------------------------------------------------------- |
    | **Input**   | *bug.v* (single-file design containing exactly one semantic bug) + *trace.log* (Verilator `--timing` or `$fatal` backtrace) |
    | **Output**  | *patch.diff* (unified diff **or** full fixed source)                                                                        |
    | **Success** | `verilator --cc` compile succeeds **and** testbench passes (use existing self-checking tb)                                  |


2. **Generate 20 task instances**:

   ```bash
   python scripts/collect_tasks.py \
     --design_roots rtlmeter/designs/OpenTitan/src \
     --num_tasks 20 --output tasks
   ```

3. **Evaluation harness**:

   ```bash
   python scripts/evaluate.py --agent agents/pydantic_fix_agent.py --tasks tasks/ --out results.json
   ```

---

## 4  Agent Design & Evaluation (Part 2)

### 4.1 Reference agent

Suggested agent baseline:

- Prompt = system spec + failing trace + bug.v snippet.

- Ask model to “produce a unified diff patch with exactly one hunk”.

- Apply with patch -p0, re-run; if still failing, give it the new trace and let it try up to 3 rounds.

```bash
python agents/pydantic_fix_agent.py \
  --task_glob tasks/*/README.yaml --save trajectories/
```

### 4.2 Run full evaluation + ablations

```bash
python evaluate.py --agent agents/pydantic_fix_agent.py --tasks tasks --out results.json
python evaluate.py --agent agents/pydantic_fix_agent.py --tasks tasks --out results_toolonly.json --no_self_refine
```

---

## 5  Reflection Prompts (Part 3)

Create `REFLECTION.md` or a slide deck covering:

* Why the agent succeeds/fails
* Scaling (model size, context window, tool call budget)
* Potential training data for Verilog bug‑fixing (e.g. OpenROAD diffs)
* Human‑in‑the‑loop strategy for >B difficulty

---

## 6  Project Layout

```
rtlmeter-llm/
├── README.md            ← (this file)
├── verilator/           ← cloned, built, installed
├── rtlmeter/            ← …
├── tasks/               ← 20 auto‑generated bug‑fix tasks
├── agents/
│   └── pydantic_fix_agent.py
├── scripts/
│   ├── collect_tasks.py
│   └── evaluate.py
└── trajectories/        ← JSONL debug traces
```

---

## 7  Uninstall / Cleanup

```bash
sudo rm -rf /usr/local/bin/verilator* /usr/local/share/verilator
rm -rf .venv verilator rtlmeter tasks trajectories
```

---

### Useful Resources

* Verilator install guide: [https://verilator.org/guide/latest/install.html](https://verilator.org/guide/latest/install.html)
* RTLMeter repo: [https://github.com/verilator/rtlmeter](https://github.com/verilator/rtlmeter)
* LangChain docs: [https://python.langchain.com](https://python.langchain.com)
