import random
from collections import deque
from typing import Deque, Tuple, List

import numpy as np
import torch


class ReplayBuffer:
    """Simple FIFO experience buffer."""
    def __init__(self, capacity: int, obs_shape: Tuple[int, ...]):
        self.capacity = capacity
        self.buffer: Deque = deque(maxlen=capacity)
        self.obs_shape = obs_shape

    def push(self, transition: Tuple[np.ndarray, int, float, np.ndarray, bool]) -> None:
        self.buffer.append(transition)

    def sample(self, batch_size: int, device: torch.device):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = map(np.stack, zip(*batch))

        states      = torch.as_tensor(states, device=device, dtype=torch.float32)
        next_states = torch.as_tensor(next_states, device=device, dtype=torch.float32)
        actions     = torch.as_tensor(actions, device=device, dtype=torch.int64).unsqueeze(1)
        rewards     = torch.as_tensor(rewards, device=device, dtype=torch.float32).unsqueeze(1)
        dones       = torch.as_tensor(dones, device=device, dtype=torch.float32).unsqueeze(1)
        return states, actions, rewards, next_states, dones

    def __len__(self) -> int:
        return len(self.buffer)
