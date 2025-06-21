# RTLMeter-LLM

This repository sets up a testing environment for various verilog and system verilog files from RTL Meter. The overall task that can be setup in this repo is defined below in section 3. The main idea is to generate a set of instance of a task (trace to fixed code) from the RTL Meter benchmark. Then, we can evaluate various models and tools on the newly collected benchmark that the repository automatically creates. 

---

## Table of Contents

1. [Project Layout](#project-layout)  
2. [10 Line Quick Start](#10-line-quick-start)  
3. [Environment Setup](#environment-setup)  
4. [Benchmark Creation](#benchmark-creation)  
5. [Agent Design & Evaluation](#agent-design--evaluation)  
6. [Useful Resources](#useful-resources)

---

## Project Layout

```
rtlmeter-llm/
├── README.md                 ← (this file)
├── verilator/                ← cloned, built, installed
├── rtlmeter/                 ← Original source benchmark to collect tasks from
├── results/                  ← JSON results of each configuration evaluation run
├── plots/                    ← Stored result plots
├── agents/
│   └── pydantic_fix_agent.py ← Agent and OpenAI LLM code. Main solve loop here
├── configs/
│   └── OpenTitan             ← Contains the 9 configurations for the evaluations
├── scripts/
│   ├── collect_tasks.py      ← Generates 20 tasks by injecting bugs into 20 system verilog files
│   ├── evaluate.py           ← Handles args for evaluation loop of all 20 tasks
│   ├── plot_results.py       ← Generates plots of the results in the output files
│   ├── run_evals.sh          ← runs all evaluations in parallel in the background
│   └── sanity_check_tasks.py ← Checks if the extracted tasks can be validated by verilator (w/o bugs yet)
├── tasks/                    ← 20 auto‑generated bug‑fix tasks; each contains a bug.sv and a trace.log file
└── trajectories/             ← JSONL debug traces
```

---

## 10 Line Quick Start

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
pip install -U pip && pip install -r rtlmeter/requirements.txt

```

---

## Environment Setup

### System packages

```bash
sudo apt update && sudo apt install -y git make autoconf g++ flex bison \
  libfl2 libfl-dev zlib1g zlib1g-dev python3-venv build-essential
```

> **Tip** Ubuntu 24.04 ships GCC‑14; Verilator compiles cleanly. If you prefer Clang:
> `sudo apt install clang` and add `CXX=clang++` before `./configure`.

### Build & install Verilator from Git

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

### Python virtual environment & RTLMeter

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r rtlmeter/requirements.txt
```

*(adds pyverilator, pytest, etc.  You’ll install LLM deps in §3.)*

### Sanity‑check installation

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

## Benchmark Creation

1. **Define the Task** — *Trace‑to‑Code Bug‑Fixing*.
  
    Concrete Definition:

    | Field       | Value                                                                                                                       |
    | ----------- | --------------------------------------------------------------------------------------------------------------------------- |
    | **Input**   | *bug.v* (single-file design containing exactly one semantic bug) + *trace.log* (Verilator `--timing` or `$fatal` backtrace) |
    | **Output**  | *fix.v* (single-file design with bugs fixed and ready to be passed into Verilator to be evaluated)                                                                        |
    | **Success** | `verilator --lint-only` compile succeeds **and** testbench passes (use existing self-checking tb)                                  |


2. **Generate 20 task instances**:

   ```bash
   python scripts/collect_tasks.py \
     --design_roots rtlmeter/designs/OpenTitan/src \
     --num_tasks 20 --output tasks
   ```

3. **Sanity-check the tasks**:

   ```bash
   python scripts/sanity_check_tasks.py tasks
   ```

4. **Evaluation Harness Example**:

   ```bash
   python scripts/evaluate.py --config configs/OpenTitan/gpt4o_mini_refine_tool.json
   ```

---

## Agent Design & Evaluation

### Design

The patch-generation agent is implemented in
[`agents/pydantic_fix_agent.py`](agents/pydantic_fix_agent.py). It wraps
OpenAI ChatCompletion and exposes Verilator verification as a tool.

* **LLM tools**
  - `run_verilator` runs `verilator --lint-only` on candidate code.
  - `apply_patch` returns the complete fixed source.

* **Self-refinement loop**
  1. Submit the buggy file and trace to the model.
  2. Process tool calls and re-test the result.
  3. Repeat with the new error trace until Verilator passes.

* **CLI toggles**
  - `--no_self_refine` stops after one round ("tool only").
  - `--no_verilator_tool` disables verification for a "refine only" run.

### Run full evaluation + ablations

This will run all configurations in the background and log the stdout to log files. 

```bash
chmod +x scripts/run_evals.sh
./scripts/run_evals.sh
```

---

## Useful Resources

* Verilator install guide: [https://verilator.org/guide/latest/install.html](https://verilator.org/guide/latest/install.html)
* RTLMeter repo: [https://github.com/verilator/rtlmeter](https://github.com/verilator/rtlmeter)
