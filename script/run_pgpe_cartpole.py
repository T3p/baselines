#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 18:36:59 2018

@author: matteo
"""

import gym
import baselines.envs.continuous_cartpole
import baselines.envs.lqg1d
from baselines.policy.pemlp_policy import PeMlpPolicy
import baselines.pgpe.npgpe as npgpe
import baselines.pgpe.pgpe as pgpe
import numpy as np

import baselines.common.tf_util as U
sess = U.single_threaded_session()
sess.__enter__()

envs = {'cartpole': 'ContCartPole-v0',
        'lqg': 'LQG1D',
        }

algos = {'pgpe': pgpe,
         'npgpe': npgpe,
        }

#Seeds: 0, 27, 62, 315, 640

def train(seed):
    DIR = '../results/pgpe/cartpole/seed_' + str(seed)
    import os
    if not os.path.exists(DIR):
        os.makedirs(DIR)
    
    env = gym.make('ContCartPole-v0')
    env.seed(seed)
    
    pol = PeMlpPolicy('pol',
                      env.observation_space,
                      env.action_space,
                      hid_size=4,
                      num_hid_layers=0,
                      diagonal=True,
                      use_bias=False,
                      standardize_input=True,
                      seed=seed)
    
    pgpe.learn(env,
              pol,
              gamma=0.99,
              step_size=1., #1e-2
              batch_size=100,
              task_horizon=200,
              max_iterations=100,
              use_baseline=True,
              step_size_strategy='norm',
              save_to=DIR,
              verbose=1,
              feature_fun=np.ravel)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--seed', help='RNG seed', type=int, default=107)
    parser.add_argument('--algo', help='Algorithm (pgpe, npgpe...)', type=int, default='pgpe')
    parser.add_argument('--env', help='Environment (RL task)', type=int, default='cartpole')
    args = parser.parse_args()
    train(args.seed)