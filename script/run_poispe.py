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
import baselines.pgpe.poisnpe as poisnpe
import baselines.pgpe.poispe as poispe
import numpy as np

import baselines.common.tf_util as U
sess = U.single_threaded_session()
sess.__enter__()

envs = {'cartpole': 'ContCartPole-v0',
        'lqg': 'LQG1D-v0',
        }

algos = {'poisnpe': poisnpe,
         'poispe': poispe,
        }

horizons = {'cartpole': 200,
            'lqg': 200,
            }

rews = {'cartpole': 10,
      'lqg': 28.8,
      }

iters = {'cartpole': 100,
         'lqg': 100,
         }

#Seeds: 107, 583, 850, 730, 808

gamma = 1.

def train(seed, env_name, algo_name, normalize, use_rmax, use_renyi):
    DIR = 'temp/'
    index = int(str(int(normalize)) + str(int(use_rmax)) + str(int(use_renyi)), 2)
    #DIR = '../results/' + algo_name + '/bound_' + str(index) + '/' + env_name + '/seed_' + str(seed)
    import os
    if not os.path.exists(DIR):
        os.makedirs(DIR)
    
    env = gym.make(envs[env_name])
    env.seed(seed)
    horizon = horizons[env_name]
    #rmax = sum([rews[env_name]*gamma**i for i in range(horizon)])
    rmax = None #Empirical
    
    pol_maker = lambda name: PeMlpPolicy(name,
                      env.observation_space,
                      env.action_space,
                      hid_layers=[],
                      diagonal=True,
                      use_bias=False,
                      seed=seed)
    
    algos[algo_name].learn(env,
              pol_maker,
              gamma=gamma,
              batch_size=100,
              task_horizon=horizon,
              max_iterations=500,
              save_to=DIR,
              verbose=2,
              feature_fun=np.ravel,
              normalize=normalize,
              use_rmax=use_rmax,
              use_renyi=use_renyi,
              max_offline_ite=100,
              max_search_ite=30,
              rmax=rmax,
              delta=0.5)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--seed', help='RNG seed', type=int, default=None)
    parser.add_argument('--normalize', help='Normalize weights?', type=int, default=1)
    parser.add_argument('--use_rmax', help='Use Rmax in bound (or var)?', type=int, default=1)
    parser.add_argument('--use_renyi', help='Use Renyi in ESS (or weight norm)?', type=int, default=1)
    parser.add_argument('--algo', help='Algorithm', type=str, default='poisnpe')
    parser.add_argument('--env', help='Environment (RL task)', type=str, default='cartpole')
    args = parser.parse_args()
    train(args.seed, args.env, args.algo, args.normalize, 
          args.use_rmax,
          args.use_renyi)
