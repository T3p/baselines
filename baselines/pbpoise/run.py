#!/usr/bin/env python3
'''
    This script runs rllab or gym environments. To run RLLAB, use the format
    rllab.<env_name> as env name, otherwise gym will be used.
'''
# Common imports
import sys, re, os, time, logging
from collections import defaultdict
import json

# Framework imports
import gym
import tensorflow as tf
import numpy as np

# Self imports: utils
from baselines.common import set_global_seeds
from baselines import logger
import baselines.common.tf_util as U
from baselines.common.rllab_utils import Rllab2GymWrapper, rllab_env_from_name
from baselines.common.atari_wrappers import make_atari, wrap_deepmind
# Self imports: algorithm
from baselines.policy.mlp_hyperpolicy import PeMlpPolicy
from baselines.pbpoise import pbpoise


def args_to_file(args, dir, filename):

    fout = dir + '/tb/' + filename + '/args.txt'
    fo = open(fout, "w")
    args_dict = vars(args)
    for k, v in args_dict.items():
        fo.write(str(k) + ' >>> ' + str(v) + '\n\n')
    fo.close()
    return


def get_env_type(env_id):
    # First load all envs
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


def train(env, policy, horizon, seed, bounded_policy,
          trainable_std, gain_init, std_init,
          njobs=1, **alg_args):

    if env.startswith('rllab.'):
        # Get env name and class
        env_name = re.match('rllab.(\w+)', env).group(1)
        env_rllab_class = rllab_env_from_name(env_name)

        # Define env maker
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
            # Atari is not tested here
            raise Exception('Not tested on atari.')
        else:
            # Not atari, standard env creation
            def make_env():
                env_rllab = gym.make(env)
                return env_rllab

    # Create the policy
    if policy == 'linear':
        hid_layers = []
    else:
        raise NotImplementedError

    def make_policy(name, ob_space, ac_space):
        return PeMlpPolicy(name, ob_space, ac_space, hid_layers,
                           deterministic=True, diagonal=True,
                           trainable_std=trainable_std,
                           use_bias=False, use_critic=False,
                           seed=seed, verbose=True,
                           hidden_W_init=U.normc_initializer(1.0),
                           std_init=tf.constant_initializer(np.log(std_init)))
    try:
        affinity = len(os.sched_getaffinity(0))
    except:
        affinity = njobs
    sess = U.make_session(affinity)
    sess.__enter__()

    set_global_seeds(seed)

    gym.logger.setLevel(logging.WARN)

    # Prepare (sequential) sampler to generate ONE trajectory at a time
    sampler = None

    # Learn
    pbpoise.learn(make_env, make_policy, horizon=horizon,
                  sampler=sampler, **alg_args)


def single_run(args, seed=None):

    # Import custom envs (must be imported here or wont work with multiple_run)
    import baselines.envs.lqg1d  # registered at import as gym env

    # Manage call from multiple runs
    if seed:
        args.seed = seed

    # Log file name
    t = time.localtime(time.time())
    tt = int(str(time.time())[-5:])
    time_str = '%s-%s-%s_%s%s%s_%s' % (
        t.tm_hour, t.tm_min, t.tm_sec, t.tm_mday, t.tm_mon, t.tm_year, tt)
    args_str = '%s_delta=%s_seed=%s' % (
        args.env.upper(), args.delta, args.seed)

    if args.filename == 'progress':
        filename = args_str + '_' + time_str
    else:
        filename = args.filename + '_' + args_str + '_' + time_str

    # Configure logger
    logger.configure(dir=args.logdir,
                     format_strs=['stdout', 'csv', 'tensorboard'],
                     file_name=filename)

    # Print args to file in logdir
    args_to_file(args, dir=args.logdir, filename=filename)

    # Learn
    train(env=args.env,
          policy=args.policy,
          horizon=args.horizon,
          seed=args.seed,
          bounded_policy=args.bounded_policy,
          trainable_std=args.trainable_std,
          gain_init=args.gain_init,  # LQG only
          std_init=args.std_init,  # LQG only
          multiple_init=args.multiple_init,
          njobs=args.njobs,
          bound_type=args.bound_type,
          delta=args.delta,
          drho=args.drho,
          gamma=args.gamma,
          max_offline_iters=args.max_offline_iters,
          max_iters=args.max_iters,
          render_after=args.render_after,
          line_search=args.line_search,
          grid_optimization=args.grid_optimization,
          truncated_mise=args.truncated_mise,
          delta_t=args.delta_t,
          filename=filename)


def multiple_runs(args):

    # Import tools for parallelizing runs
    from joblib import Parallel, delayed

    seed = []
    # for i in [n/10 for n in range(1, 8)]:
    for k in range(1, 5):
        seed.append(k)

    # Parallelize single runs
    n_jobs = len(seed)
    Parallel(n_jobs=n_jobs)(delayed(single_run)(
        args,
        seed=seed[i]
        ) for i in range(n_jobs))


def main(args):
    import argparse

    # Easily add a boolean argument to the parser with default value
    def add_bool_arg(parser, name, default=False):
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--' + name, dest=name, action='store_true')
        group.add_argument('--no-' + name, dest=name, action='store_false')
        parser.set_defaults(**{name: default})

    # Command line arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--seed', help='RNG seed', type=int, default=0)
    parser.add_argument('--env', type=str, default='LQG1D-v0')
    parser.add_argument('--horizon', type=int, default=20)
    parser.add_argument('--bound_type', type=str, default='max-renyi')
    parser.add_argument('--filename', type=str, default='progress')
    parser.add_argument('--logdir', type=str, default='logs')
    parser.add_argument('--gain_init', type=float, default=-0.1)  # LQG only
    parser.add_argument('--std_init', type=float, default=0.15)  # LQG only
    parser.add_argument('--delta', type=float, default=0.2)
    parser.add_argument('--drho', type=float, default=1)
    parser.add_argument('--njobs', type=int, default=-1)
    parser.add_argument('--policy', type=str, default='linear')
    parser.add_argument('--max_iters', type=int, default=1000)
    parser.add_argument('--max_offline_iters', type=int, default=10)
    parser.add_argument('--render_after', type=int, default=None)
    parser.add_argument('--gamma', type=float, default=0.99)
    parser.add_argument('--line_search', type=str, default=None)  # 'parabola'
    parser.add_argument('--multiple_init', type=int, default=None)
    parser.add_argument('--grid_optimization', type=int, default=None)
    parser.add_argument('--delta_t', type=str, default=None)
    add_bool_arg(parser, 'bounded_policy', default=True)
    add_bool_arg(parser, 'trainable_std', default=True)
    add_bool_arg(parser, 'truncated_mise', default=True)
    add_bool_arg(parser, 'experiment', default=False)
    args = parser.parse_args(args)

    if args.experiment:
        multiple_runs(args)
    else:
        single_run(args)


if __name__ == '__main__':
    main(sys.argv[1:])
