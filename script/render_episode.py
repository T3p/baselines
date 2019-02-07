#!/usr/bin/env python3
# noinspection PyUnresolvedReferences
'''
    This file is intended to be used to render an episode for a given policy
    and a given environment.

    TODO:
    - Understand rendering in RLLAB
    - Understand rendering in remote server

'''
# Common imports
import sys, re, os, time, logging
from collections import defaultdict
import pickle as pkl

# Framework imports
import gym
import tensorflow as tf

# Self imports: utils
from baselines.common import set_global_seeds
from baselines import logger
import baselines.common.tf_util as U
from baselines.common.rllab_utils import Rllab2GymWrapper, rllab_env_from_name
from baselines.common.atari_wrappers import make_atari, wrap_deepmind
# Self imports: algorithm
from baselines.policy.mlp_policy import MlpPolicy
from baselines.policy.cnn_policy import CnnPolicy
from baselines.pois import pois
from baselines.pois.parallel_sampler import ParallelSampler

def get_env_type(env_id):
    #First load all envs
    _game_envs = defaultdict(set)
    for env in gym.envs.registry.all():
        # TODO: solve this with regexes
        env_type = env._entry_point.split(':')[0].split('.')[-1]
        _game_envs[env_type].add(env.id)
    # Get env type
    env_type = None
    for g, e in _game_envs.items():
        if env_id in e:
            env_type = g
            break
    return env_type

def play_episode(env, pi, gamma):

    ob = env.reset()
    done = False
    reward = 0
    disc = 1.0
    timesteps = 0
    while not done:
        ac, vpred = pi.act(True, ob)
        ob, r, done, _ = env.step(ac)
        reward = r * disc
        disc *= gamma
        timesteps += 1
        print(ob)
        r = env.render(mode='rgb_array')
        print(r)
    print("Finished episode.")
    print("Total timesteps:", timesteps)
    print("Total reward:", reward)

def main():
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--seed', help='RNG seed', type=int, default=0)
    parser.add_argument('--env', type=str, default='cartpole')
    parser.add_argument('--policy', type=str, default='nn')
    parser.add_argument('--policy_file', type=str, default=None)
    parser.add_argument('--gamma', type=float, default=1.0)
    args = parser.parse_args()

    # Session
    sess = U.single_threaded_session()
    sess.__enter__()

    env = args.env
    # Create the environment
    if env.startswith('rllab.'):
        # Get env name and class
        env_name = re.match('rllab.(\S+)', env).group(1)
        env_rllab_class = rllab_env_from_name(env_name)
        # Define env maker
        def make_env():
            env_rllab = env_rllab_class()
            _env = Rllab2GymWrapper(env_rllab)
            return _env
        # Used later
        env_type = 'rllab'
    else:
        # Normal gym, get if Atari or not.
        env_type = get_env_type(env)
        assert env_type is not None, "Env not recognized."
        # Define the correct env maker
        if env_type == 'atari':
            # Atari, custom env creation
            def make_env():
                _env = make_atari(env)
                return wrap_deepmind(_env)
        else:
            # Not atari, standard env creation
            def make_env():
                env_rllab = gym.make(env)
                return env_rllab
    env = make_env()
    env.seed(args.seed)
    ob_space = env.observation_space
    ac_space = env.action_space

    # Make policy
    policy = args.policy
    if policy == 'linear':
        hid_size = num_hid_layers = 0
    elif policy == 'nn':
        hid_size = [100, 50, 25]
        num_hid_layers = 3
    # Temp initializer
    policy_initializer = U.normc_initializer(0.0)
    if policy == 'linear' or policy == 'nn':
        def make_policy(name, ob_space, ac_space):
            return MlpPolicy(name=name, ob_space=ob_space, ac_space=ac_space,
                             hid_size=hid_size, num_hid_layers=num_hid_layers, gaussian_fixed_var=True, use_bias=False, use_critic=False,
                             hidden_W_init=policy_initializer,
                             output_W_init=policy_initializer)
    elif policy == 'cnn':
        def make_policy(name, ob_space, ac_space):
            return CnnPolicy(name=name, ob_space=ob_space, ac_space=ac_space,
                         gaussian_fixed_var=True, use_bias=False, use_critic=False,
                         hidden_W_init=policy_initializer,
                         output_W_init=policy_initializer)
    else:
        raise Exception('Unrecognized policy type.')
    pi = make_policy('pi', ob_space, ac_space)
    # Load policy weights from file
    all_var_list = pi.get_trainable_variables()
    var_list = [v for v in all_var_list if v.name.split('/')[1].startswith('pol')]
    set_parameter = U.SetFromFlat(var_list)

    weights = pkl.load(open(args.policy_file, 'rb'))
    pi.set_param(weights)

    play_episode(env, pi, args.gamma)


if __name__ == '__main__':
    main()
