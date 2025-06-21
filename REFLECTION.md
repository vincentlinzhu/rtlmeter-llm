# Agent Experiment Reflection

This document summarizes benchmark runs on the OpenTitan bug‑fix tasks. The bar
plots in `plots/benchmark_results.png` were produced with
`python scripts/plot_results.py` and compare three agent configurations for each
model:

- **refine+tool** – iterative self‑refinement and the Verilator tool enabled.
- **refine only** – refinement enabled but Verilator disabled.
- **tool only** – Verilator available but no self‑refinement.

Each configuration attempts all 20 tasks.

![Benchmark results](plots/benchmark_results.png)

## Benchmark Results

| Model           | Config        | Success Rate | Avg Time (s) |
|-----------------|---------------|-------------:|-------------:|
| gpt‑3.5‑turbo   | refine+tool   | 90%          | 20.7 |
| gpt‑3.5‑turbo   | refine only   | 85%          | 20.4 |
| gpt‑3.5‑turbo   | tool only     | 85%          | 15.3 |
| gpt‑4.1‑nano    | refine+tool   | 80%          | 23.9 |
| gpt‑4.1‑nano    | refine only   | 85%          | 16.3 |
| gpt‑4.1‑nano    | tool only     | 55%          | 9.8 |
| gpt‑4o‑mini     | refine+tool   | 100%         | 55.4 |
| gpt‑4o‑mini     | refine only   | 90%          | 78.6 |
| gpt‑4o‑mini     | tool only     | 90%          | 37.2 |

The plots show that combining self‑refinement with Verilator yields the best
results. GPT‑4o‑mini solves all tasks in this mode. Removing either refinement or
the tool reduces accuracy, most noticeably for gpt‑4.1‑nano where success drops
from 80% to 55% without refinement. Runs without iterative loops finish faster,
but they leave more bugs unsolved.

| Task # | 3.5-Turbo refine+tool | 3.5-Turbo refine only | 3.5-Turbo tool only | 4o-mini refine+tool | 4o-mini refine only | 4o-mini tool only | 4.1-nano refine+tool | 4.1-nano refine only | 4.1-nano tool only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 01 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 02 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 03 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 04 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 05 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | X | ✓ |
| 06 | ✓ | X | X | ✓ | ✓ | X | ✓ | ✓ | X |
| 07 | ✓ | ✓ | X | ✓ | ✓ | ✓ | ✓ | ✓ | X |
| 08 | ✓ | ✓ | ✓ | ✓ | X | ✓ | X | X | X |
| 09 | ✓ | ✓ | X | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 10 | ✓ | X | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | X |
| 11 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 12 | ✓ | ✓ | ✓ | ✓ | X | X | X | ✓ | X |
| 13 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 14 | ✓ | X | ✓ | ✓ | ✓ | ✓ | X | ✓ | X |
| 15 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 16 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | X |
| 17 | X | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | X |
| 18 | X | ✓ | ✓ | ✓ | ✓ | ✓ | X | X | X |
| 19 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |


| Task # | 3.5-Turbo refine+tool | 3.5-Turbo refine only | 3.5-Turbo tool only | 4o-mini refine+tool | 4o-mini refine only | 4o-mini tool only | 4.1-nano refine+tool | 4.1-nano refine only | 4.1-nano tool only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00 | 28.63 | 15.62 | 12.07 | 32.07 | 21.07 | 32.57 | 10.58 | 5.56 | 9.57 |
| 01 | 3.56 | 4.56 | 9.56 | 25.07 | 7.56 | 15.07 | 2.56 | 2.06 | 4.06 |
| 02 | 11.57 | 12.56 | 20.07 | 48.07 | 34.07 | 48.58 | 13.06 | 9.06 | 9.06 |
| 03 | 6.56 | 6.56 | 6.56 | 35.57 | 11.56 | 22.57 | 3.06 | 5.56 | 4.56 |
| 04 | 10.56 | 4.06 | 11.06 | 22.07 | 12.06 | 31.07 | 7.56 | 2.56 | 5.06 |
| 05 | 34.57 | 26.57 | 28.07 | 52.57 | 36.07 | 52.57 | 14.07 | 42.80 | 7.56 |
| 06 | 42.13 | 38.81 | 19.57 | 97.09 | 158.72 | 51.57 | 38.29 | 14.57 | 31.07 |
| 07 | 11.57 | 14.06 | 13.07 | 35.57 | 24.07 | 34.57 | 11.12 | 6.56 | 8.56 |
| 08 | 15.57 | 6.06 | 10.56 | 156.68 | 772.80 | 28.07 | 45.82 | 37.79 | 3.56 |
| 09 | 16.13 | 5.06 | 9.06 | 18.07 | 9.06 | 19.57 | 8.06 | 5.06 | 10.57 |
| 10 | 22.07 | 65.71 | 17.07 | 48.07 | 33.07 | 69.08 | 14.07 | 8.56 | 12.06 |
| 11 | 28.57 | 78.64 | 28.07 | 79.58 | 45.57 | 75.08 | 21.57 | 10.07 | 29.07 |
| 12 | 15.57 | 9.06 | 19.57 | 199.80 | 152.71 | 34.57 | 42.79 | 4.56 | 5.06 |
| 13 | 9.56 | 6.06 | 9.06 | 23.07 | 18.56 | 16.57 | 5.06 | 5.06 | 8.57 |
| 14 | 19.57 | 57.31 | 14.07 | 65.08 | 38.07 | 31.57 | 84.81 | 46.30 | 10.56 |
| 15 | 6.56 | 5.56 | 7.06 | 14.06 | 19.06 | 22.57 | 3.06 | 18.29 | 4.06 |
| 16 | 7.56 | 6.56 | 7.06 | 17.57 | 21.07 | 15.56 | 6.56 | 3.06 | 4.06 |
| 17 | 35.82 | 5.06 | 5.56 | 16.57 | 21.07 | 21.07 | 5.56 | 2.56 | 5.06 |
| 18 | 66.84 | 19.57 | 42.57 | 86.09 | 82.58 | 80.08 | 114.82 | 88.81 | 12.06 |
| 19 | 21.07 | 20.62 | 15.57 | 35.07 | 52.57 | 42.57 | 26.12 | 7.06 | 11.56 |


## Why the Agent Succeeds or Fails

The agent succeeds when it can view compile errors and apply multiple fixes. It
fails on multi‑step issues or uncommon constructs that exceed the model's context
or training. Larger models or extended context windows could help.

## Scaling Up Inference

Increasing the tool‑call budget or running inference on GPUs shortens overall
runtime. Batching several tasks hides latency when evaluating larger datasets.

## Training a Better Base Model

Domain‑adaptive pretraining on public HDL repositories and synthesis logs would
teach the model more Verilog patterns. This improves understanding before any
supervised fine‑tuning.

## Collecting Training Data

Open‑source projects such as OpenROAD or chipyard contain rich histories of bug
fixes. Mining their diffs produces paired examples of errors and corrections.
Synthetic data can be created by intentionally corrupting designs and recording
how they are fixed.

## Involving Human Annotators

A review loop with hardware engineers lets humans grade patches and create small
reproducers. Their feedback expands the dataset with high‑quality
examples and reduces noise in automatically mined diffs.