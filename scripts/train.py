import argparse
from pathlib import Path

import gymnasium as gym
import yaml

from lunarlander.agents.dqn_agent import DQNAgent


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="configs/default.yaml")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save_dir", type=str, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())

    env = gym.make("LunarLander-v3")
    env.reset(seed=args.seed)

    if args.save_dir is not None:
        save_root = Path(args.save_dir)
    else:
        save_root = Path(
            Path.cwd().joinpath("models")
            if (dm := Path.cwd() / "models").exists()
            else Path(Path.home(), ".cache", "lunarlander")
        )
    agent = DQNAgent(env, cfg, save_root)
    agent.train_forever()


if __name__ == "__main__":
    main()
