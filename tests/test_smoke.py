import gymnasium as gym
from lunarlander.networks.q_network import QNetwork


def test_forward():
    env = gym.make("LunarLander-v3")
    obs_dim = env.observation_space.shape[0]
    act_dim = env.action_space.n
    net = QNetwork(obs_dim, act_dim)
    assert net
    env.close()
