# rtlmeter-llm

Copy‑paste the commands below (tested on Ubuntu 22.04 / macOS 14 with Homebrew) and adapt as needed.

---

## 0  TL;DR (10‑line quick‑start)

```bash
# 1. clone repos
mkdir rtlmeter‑llm && cd $_
git clone https://github.com/verilator/verilator.git
git clone https://github.com/verilator/rtlmeter.git

# 2. system deps — Ubuntu; see §1.1 for macOS/Homebrew variant
sudo apt update && sudo apt install -y git make autoconf g++ flex bison \
  libfl2 libfl-dev zlib1g zlib1g-dev python3-venv

# 3. build & install Verilator (≈2‑3 min on 8‑core laptop)
cd verilator && git checkout stable && autoconf && ./configure && make -j$(nproc) && sudo make install && cd ..

# 4. python env + RTLMeter deps
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -r rtlmeter/requirements.txt openai langchain[all] pandas jinja2 rich

# 5. smoke‑test one design via RTLMeter harness
cd rtlmeter && python run.py --design designs/amber23/sha256 --tool verilator
```

If the run passes you’re ready to start Parts 1‑3.

---

### macOS 14 (Homebrew) Quick‑Start

```bash
# 0. Prerequisites — install Xcode Command Line Tools (compiler, make, git)
xcode-select --install  # skip if already installed

# 1. Clone repos
mkdir rtlmeter-llm && cd $_
git clone https://github.com/verilator/verilator.git
git clone https://github.com/verilator/rtlmeter.git

# 2. System dependencies via Homebrew
brew update && brew install autoconf automake bison flex gawk gnu-sed gpatch \
  libtool make coreutils pkg-config git python@3.12

# 3. Ensure Homebrew Python in PATH (feel free to append to ~/.zprofile)
export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"
python3 -m pip install --upgrade pip

# 4. Build & install Verilator (≈2–3 min on Apple M‑series)
cd verilator && git checkout stable && autoconf && ./configure && make -j$(sysctl -n hw.ncpu) && sudo make install && cd ..

# 5. Python venv + RTLMeter deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r rtlmeter/requirements.txt openai langchain[all] pandas jinja2 rich

# 6. Smoke‑test one design via RTLMeter harness
cd rtlmeter && python run.py --design designs/amber23/sha256 --tool verilator
```

If the run passes you’re ready to dive into Parts 1‑3.

---

## 1  Prerequisites

| Tool               | Version tested                       | Install notes                           |
| ------------------ | ------------------------------------ | --------------------------------------- |
| **Python**         |  ≥ 3.10                              | `sudo apt install python3 python3-venv` |
| **GCC / Clang**    |  ≥ 11                                | default on Ubuntu 22.04 / Xcode 15      |
| **Git**            | latest                               |                                         |
| **Verilator**      |  5.026‑dev (built from `stable` tag) | built from source; see §2.2             |
| **RTLMeter**       |  master (June 2025)                  | cloned from GitHub                      |
| **OpenAI API key** | env var `OPENAI_API_KEY`             | required for agent evaluation           |

> **macOS users** — `brew install autoconf automake bison flex gawk gnu-sed gpatch libtool git make coreutils` before §2.2 commands.

---

## 2  Environment Setup

### 2.1 System packages

**Ubuntu 22.04**

```bash
sudo apt update && sudo apt install -y git make autoconf g++ flex bison \
  libfl2 libfl-dev zlib1g zlib1g-dev python3-venv
```

**macOS 14 / Homebrew**

```bash
brew update && brew install autoconf automake bison flex gawk gnu-sed gpatch \
  libtool make coreutils pkg-config git python@3.12
# (optional) add Python to PATH if not already)
export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"
```

> On macOS, Homebrew’s `python@3.12` provides `pip`, `venv`, and headers under `/opt/homebrew`. Use `python3` from that location or fully‑qualified path as above.

### 2.2 Build & install Verilator (Git Quick‑Install) Build & install Verilator (Git Quick‑Install)

```bash
# in repo root
cd verilator
# (optional) pin a known‑good commit
git checkout stable  # tag that tracks latest release‑ready commit

# build
autoconf               # generates configure script
./configure            # checks deps
make -j$(nproc)        # compile (≈1–3 min)

# install to /usr/local
sudo make install

# verify
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

> The default `requirements.txt` pins `pytest`, `pyverilator`, etc.  You’ll add LLM packages in §3.

### 2.4 Sanity‑check installation

```bash
cd rtlmeter
python run.py --design designs/amber23/sha256 --tool verilator --timeout 60
```

Expect a summary like `PASSED (1/1)`.

---

## 3  Benchmark Creation (Part 1)

1. **Define the Task**  (suggestion — *“Trace‑to‑Code Bug‑Fixing”*)

   * **Input**: (a) failing Verilator trace, (b) original Verilog file.
   * **Output**: patched Verilog that passes the provided RTLMeter test.
   * **Goal**: minimise diff size while resolving failure.

2. **Collect 20 Task Instances**

   ```bash
   # script: scripts/collect_tasks.py (example skeleton)
   python scripts/collect_tasks.py \
       --design_roots designs/amber23 designs/picorv32 \
       --num_tasks 20 --output tasks/
   ```

   The script can randomly corrupt one line in each design with an LLM (`gpt‑4o`) to introduce a single‑point bug, then store:

   ```text
   tasks/0001/{orig.v, bug.v, trace.log, README.yaml}
   ```

3. **Install LLM/agent deps**

   ```bash
   pip install openai==1.* langchain==0.2.* tiktoken git+https://github.com/codellama/agentic
   export OPENAI_API_KEY=<your‑key>
   ```

4. **Evaluation Harness**

   * **Metrics**: *Pass\@1*, diff size, Verilator warnings, runtime.
   * **Harness script**: `python evaluate.py --agent my_agent.py --tasks tasks/ --out results.json`.

---

## 4  Agent Design & Evaluation (Part 2)

### 4.1 Reference agent (`agents/pydantic_fix_agent.py`)

```bash
python agents/pydantic_fix_agent.py --task_glob tasks/*/README.yaml --save trajectories/
```

The agent chain:

1. Generates patch with system prompt (spec + failure trace).
2. Applies patch, re‑runs RTLMeter.
3. If fail → self‑refine up to 3 rounds.

### 4.2 Run full evaluation + ablations

```bash
python evaluate.py --agent agents/pydantic_fix_agent.py --tasks tasks --out results.json
python evaluate.py --agent agents/pydantic_fix_agent.py --tasks tasks --out results_toolonly.json --no_self_refine
```

---

## 5  Reflection Prompts (Part 3)

Create a short slide deck or `REFLECTION.md` answering:

* **Performance analysis** — why does the agent succeed/fail?
* **Scaling inference** — which model / context window / tool call budget?
* **Training data** — where to mine Verilog commit diffs? (e.g. OpenROAD, CORE‑V‑MCU)
* **Human‑in‑the‑loop** — propose putting engineers at difficulty tiers > B.

---

## 6  Project Layout

```
rtlmeter‑llm/
├── README.md               ← (this file)
├── verilator/              ← cloned, built, installed
├── rtlmeter/
│   └── …
├── tasks/                  ← 20 auto‑generated bug‑fix tasks
├── agents/
│   ├── pydantic_fix_agent.py
│   └── …
├── scripts/
│   ├── collect_tasks.py
│   └── evaluate.py
└── trajectories/           ← JSONL debug traces
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
