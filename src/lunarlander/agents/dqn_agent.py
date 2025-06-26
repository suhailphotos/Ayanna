from pathlib import Path
from typing import Dict

import gymnasium as gym
import numpy as np
import torch
import torch.nn.functional as F
from torch.optim import Adam
from tqdm import tqdm

from lunarlander.networks.q_network import QNetwork
from lunarlander.replay_buffer import ReplayBuffer

DEFAULT_HYPERS: Dict = {
    "gamma": 0.99,
    "lr": 1e-3,
    "epsilon_start": 1.0,
    "epsilon_end": 0.05,
    "epsilon_decay": 2.5e5,
    "buffer_capacity": 100_000,
    "batch_size": 64,
    "target_update_freq": 1_000,
    "train_start": 5_000,
    "total_steps": 1_000_000,
    "eval_every": 50_000,
    "max_episode_len": 1_000,
}


class DQNAgent:
    def __init__(self, env: gym.Env, cfg: Dict, save_dir: Path):
        self.env = env
        self.cfg = {**DEFAULT_HYPERS, **cfg}
        for k in ["gamma", "lr", "epsilon_start", "epsilon_end", "epsilon_decay"]:
            if k in self.cfg:
                try:
                    self.cfg[k] = float(self.cfg[k])
                except Exception:
                    pass
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        obs_dim = env.observation_space.shape[0]
        act_dim = env.action_space.n

        self.policy_net = QNetwork(obs_dim, act_dim).to(self.device)
        self.target_net = QNetwork(obs_dim, act_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()                      # target in inference-only mode

        self.optimizer = Adam(self.policy_net.parameters(), lr=self.cfg["lr"])
        self.replay_buffer = ReplayBuffer(self.cfg["buffer_capacity"], env.observation_space.shape)

        self.step_count = 0
        self.epsilon = self.cfg["epsilon_start"]

    # ─────────────────────────── Public API ──────────────────────────────
    def train_forever(self):
        pbar = tqdm(total=self.cfg["total_steps"], desc="Training")
        episode = 0
        while self.step_count < self.cfg["total_steps"]:
            state, _ = self.env.reset(seed=None)
            ep_reward = 0.0

            for _ in range(self.cfg["max_episode_len"]):
                action = self._select_action(state)
                next_state, reward, terminated, truncated, _ = self.env.step(action)
                done = terminated or truncated

                self.replay_buffer.push((state, action, reward, next_state, done))
                state = next_state
                ep_reward += reward
                self.step_count += 1
                pbar.update(1)

                # learn
                if self.step_count > self.cfg["train_start"] and \
                   self.step_count % 4 == 0:
                    self._learn()

                # target network hard update
                if self.step_count % self.cfg["target_update_freq"] == 0:
                    self.target_net.load_state_dict(self.policy_net.state_dict())

                # periodic checkpoint
                if self.step_count % self.cfg["eval_every"] == 0:
                    self._checkpoint(name=f"policy_step_{self.step_count:07d}.pt")

                if done or self.step_count >= self.cfg["total_steps"]:
                    break

            episode += 1
            pbar.set_postfix({"episode": episode, "ep_reward": ep_reward, "epsilon": self.epsilon})

        pbar.close()
        self._checkpoint(name="policy_final.pt")
        print("Training finished ✔")

    # ──────────────────────────── Internals ──────────────────────────────
    def _select_action(self, state):
        # ε-greedy annealed linearly
        self.epsilon = max(
            self.cfg["epsilon_end"],
            self.cfg["epsilon_start"] - self.step_count / self.cfg["epsilon_decay"]
        )

        if np.random.rand() < self.epsilon:
            return self.env.action_space.sample()

        state_t = torch.as_tensor(state, device=self.device, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            q_values = self.policy_net(state_t)
        return int(torch.argmax(q_values, dim=1).item())

    def _learn(self):
        if len(self.replay_buffer) < self.cfg["batch_size"]:
            return

        s, a, r, s_next, d = self.replay_buffer.sample(self.cfg["batch_size"], self.device)

        # Current Q
        q_pred = self.policy_net(s).gather(1, a)

        # Target Q
        with torch.no_grad():
            q_next = self.target_net(s_next).max(1, keepdim=True)[0]
            q_target = r + (1 - d) * self.cfg["gamma"] * q_next

        loss = F.mse_loss(q_pred, q_target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def _checkpoint(self, name: str):
        torch.save(self.policy_net.state_dict(), self.save_dir / name)
