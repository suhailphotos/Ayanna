# LunarLander‑v3 — Deep‑Q Network Showcase

A **from‑scratch** implementation of a Deep‑Q Network (DQN) agent that lands the Lunar Lander using **two fully‑connected networks** (policy + target) and a replay buffer.
This repo doubles as a *production‑style template* for small‑scale reinforcement‑learning projects, demonstrating all steps from install to reproducible video outputs.

* **Frameworks**: PyTorch 2, Gymnasium (Box2D), Poetry + Conda
* **Highlights:**

  * Manual neural‑net definition (`torch.nn.Linear` layers only)
  * Hard‑update target network every *1 000* steps
  * 1 M training steps ≈ **200+ reward** agent (solves the task)
  * One‑command evaluation + MP4 recording
  * All artefacts stored under a **global model cache** (`$NEBULA_AI_MODELS` or `models/` symlink)

---

## Table of Contents

1. [Project layout](#project-layout)
2. [Quick start](#quick-start)
3. [How it works](#how-it-works)
4. [Results](#results)
5. [Troubleshooting & FAQ](#troubleshooting--faq)
6. [Background reading](#background-reading)
7. [License](#license)

---

## Project layout

```
.
├── configs/            # YAML hyper‑parameter sets
├── scripts/            # CLI entry‑points
│   ├── train.py
│   └── evaluate.py
├── src/lunarlander/    # Core library (importable)
│   ├── agents/
│   ├── networks/
│   ├── replay_buffer.py
│   └── …
├── tests/              # PyTest smoke checks
├── models/             # ⇢ linked to $NEBULA_AI_MODELS/custom/lunarlander
├── environment.yml     # Conda descriptor
├── pyproject.toml      # Poetry metadata
├── recordings/         # MP4 evaluation outputs
└── README.md           # ← you are here
```

| Path                        | Purpose                                       |
| --------------------------- | --------------------------------------------- |
| **`agents/dqn_agent.py`**   | Training loop, ε‑greedy schedule, checkpoints |
| **`networks/q_network.py`** | 3‑layer perceptron ⇒ Q(s, a)                  |
| **`replay_buffer.py`**      | FIFO buffer, uniform sampling                 |
| **`scripts/train.py`**      | Spawn env, parse config, launch training      |
| **`scripts/evaluate.py`**   | Human window **or** off‑screen MP4            |

---

## Quick start

> **Tested on macOS 14 (CPU) and Ubuntu 22.04 (RTX A2000).**

```bash
# 1 – Create & activate environment
conda env create -f environment.yml
conda activate lunarlander
poetry install --no-root        # uses active Conda Python

mkdir -p "$NEBULA_AI_MODELS/custom/lunarlander"
ln -s "$NEBULA_AI_MODELS/custom/lunarlander" models

python scripts/train.py --config configs/default.yaml

python scripts/evaluate.py --weights models/policy_final.pt

python scripts/evaluate.py --weights models/policy_final.pt --record
```

### Common install pitfalls & gotchas

* **Editable install fails:**
  If you run `pip install -e src` you'll get
  `ERROR: ...src does not appear to be a Python project: neither 'setup.py' nor 'pyproject.toml' found.`
  **Fix:**

  ```bash
  pip install -e .
  ```

  (The main `pyproject.toml` declares `src/lunarlander` as a package.)

* **MP4 recording fails / moviepy missing:**
  If you see
  `ModuleNotFoundError: No module named 'moviepy'`
  **Fix:**
  Add to `environment.yml` under pip:

  ```yaml
      - gymnasium[other]
  ```

  Then re-run:

  ```bash
  pip install -r requirements.txt  # or: poetry install --no-root
  ```

* **Model checkpoints not found:**

  * Make sure `models/` exists and is not a broken symlink.
  * If the target directory of your `models` symlink doesn't exist, training falls back to `~/.cache/lunarlander/`.
  * **Fix:** Create the symlink's target dir before training:

    ```bash
    mkdir -p "$NEBULA_AI_MODELS/custom/lunarlander"
    ln -sf "$NEBULA_AI_MODELS/custom/lunarlander" models
    ```

* **Why only 2 episodes recorded?**
  By default, Gymnasium records only selected episodes.
  This repo uses:

  ```python
  RecordVideo(..., episode_trigger=lambda episode_id: True)
  ```

  so **all episodes in evaluation get saved**. If you see fewer, clean out `recordings/` and re-run.

* **Cannot import your own package in scripts?**
  Scripts must be run from the **project root** so that `src/lunarlander` is importable.
  (Not from `scripts/`.)

---

## How it works

### Dual‑network DQN in 60 seconds

```
state  ─┐                ┌─> max_a′ Q_target(s′, a′)
        │  policy net    │
        ├──────────────> Q(s, a) ─┐
        │                        │ Bellman target
action ◀┘                        ▼
Replay Buffer  –– sample ––>  TD‑error ––> back‑prop → policy net
                                ▲
Every N steps  –– hard copy –––––┘
```

* **Policy net (θ):** live network we optimise.
* **Target net (θ⁻):** slow‑moving reference → stabilises learning.
* **Replay buffer:** decorrelates samples → better gradient estimates.

> Loss: \$(r + γ(1-d),\max\_{a′}Q\_{θ^-}(s′,a′) - Q\_{θ}(s,a))^{2}\$

See [`agents/dqn_agent.py::_learn()`](src/lunarlander/agents/dqn_agent.py) for the exact PyTorch ops.

### Hyper‑parameters ([default.yaml](configs/default.yaml))

|  parameter           | value       | rationale                            |
| -------------------- | ----------- | ------------------------------------ |
| `buffer_capacity`    | 100 k       | fits comfortably in RAM              |
| `batch_size`         | 64          | good GPU utilisation w/o OOM         |
| `epsilon_decay`      | 250 k steps | ≈25 % of total training span         |
| `target_update_freq` | 1 k         | empirical sweet‑spot for LunarLander |

---

## Results

A typical run converges to **≥ 200** average reward (solved) after \~750 k steps on an RTX A2000.

| Checkpoint | Avg. reward\* | Notes              |
| ---------- | ------------- | ------------------ |
| 0          | −250          | random policy      |
| 100 k      | −50           | hovering stage     |
| 500 k      | +140          | soft landings 70 % |
| 1 M        | **+220**      | task solved        |

\* 5‑episode mean, deterministic policy.

<p align="center">
  <img alt="Landing GIF" src="./docs/landing.gif" width="480"/>
</p>

---

## Troubleshooting & FAQ

| Symptom                                     | Fix                                                                               |
| ------------------------------------------- | --------------------------------------------------------------------------------- |
| `pip install -e src` → *no pyproject found* | Run `pip install -e .` from project root.                                         |
| `ModuleNotFoundError: moviepy`              | Add `gymnasium[other]` to your environment and re-install.                        |
| `ImportError: Box2D`                        | `conda install box2d-py` **or** ensure `gymnasium[box2d]` extra pulled the wheel. |
| SDL window hangs on WSL                     | Use `--record` to render off‑screen and play the MP4.                             |
| CUDA out‑of‑memory                          | Lower `batch_size`, or set `CUDA_VISIBLE_DEVICES=` to force CPU.                  |
| Checkpoints not saved                       | Ensure `models/` exists and is not a broken symlink.                              |

---

## Background reading

* Sutton & Barto — *Reinforcement Learning: An Introduction* (2nd ed.)
* Mnih et al., 2015 — *Human‑level control through deep reinforcement learning*
* OpenAI Spinning‑Up — excellent practical guides

---

## License

[MIT](./LICENSE) — free to fork, star & iterate.

---


