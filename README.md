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

# 5. Smoke‑test a design via RTLMeter harness
cd rtlmeter && python run.py --design designs/amber23/sha256 --tool verilator
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
python rtlmeter/run.py \
  --design designs/amber23/sha256 \
  --tool verilator \
  --timeout 60

```

Expect `PASSED (1/1)`.

---

## 3  Benchmark Creation (Part 1)

1. **Define the Task** — *Trace‑to‑Code Bug‑Fixing*.
2. **Generate 20 task instances**:

   ```bash
   python scripts/collect_tasks.py \
     --design_roots designs/amber23 designs/picorv32 \
     --num_tasks 20 --output tasks/
   ```
3. **Install LLM/agent deps**:

   ```bash
   pip install openai==1.* langchain==0.2.* tiktoken \
     git+https://github.com/codellama/agentic
   export OPENAI_API_KEY=<your-key>
   ```
4. **Evaluation harness**:

   ```bash
   python evaluate.py --agent my_agent.py --tasks tasks/ --out results.json
   ```

---

## 4  Agent Design & Evaluation (Part 2)

### 4.1 Reference agent

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
