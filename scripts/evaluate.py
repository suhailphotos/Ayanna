"""Render a trained policy (human window or mp4)."""
import argparse
from pathlib import Path

import gymnasium as gym
import torch
from gymnasium.wrappers import RecordVideo

from lunarlander.networks.q_network import QNetwork


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True, type=str, help="*.pt checkpoint")
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--fps", type=int, default=50)
    ap.add_argument("--record", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    render_mode = "rgb_array" if args.record else "human"
    env = gym.make("LunarLander-v3", render_mode=render_mode)
    if args.record:
        env = RecordVideo(
            env,
            video_folder="recordings",
            name_prefix="dqn",
            episode_trigger=lambda episode_id: True  # Record EVERY episode!
        )

    obs_dim = env.observation_space.shape[0]
    act_dim = env.action_space.n
    policy = QNetwork(obs_dim, act_dim).to(device)
    policy.load_state_dict(torch.load(args.weights, map_location=device))
    policy.eval()

    for ep in range(args.episodes):
        state, _ = env.reset(seed=ep)
        done = False
        while not done:
            with torch.no_grad():
                state_t = torch.as_tensor(state, device=device, dtype=torch.float32).unsqueeze(0)
                action = int(torch.argmax(policy(state_t)))
            state, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            if args.record:
                env.render()  # off-screen capture
        print(f"Episode {ep} finished.")

    env.close()


if __name__ == "__main__":
    main()
