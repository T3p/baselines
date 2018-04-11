#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  4 18:13:18 2018

@author: matteo
"""
"""References
    PGPE: Sehnke, Frank, et al. "Policy gradients with parameter-based exploration for
        control." International Conference on Artificial Neural Networks. Springer,
        Berlin, Heidelberg, 2008.
    Optimal baseline: Zhao, Tingting, et al. "Analysis and
        improvement of policy gradient estimation." Advances in Neural
        Information Processing Systems. 2011.
"""

import numpy as np
from baselines import logger


def eval_trajectory(env, pol, gamma, task_horizon, feature_fun):
    ret = disc_ret = 0
    
    t = 0
    ob = env.reset()
    done = False
    while not done and t<task_horizon:
        s = feature_fun(ob) if feature_fun else ob
        a = pol.act(s)
        ob, r, done, _ = env.step(a)
        ret += r
        disc_ret += gamma**t * r
        t+=1
        
    return ret, disc_ret, t
        

def learn(env, pol, gamma, step_size, batch_size, task_horizon, max_iterations, 
          feature_fun=None, use_baseline=True, step_size_strategy=None, 
          verbose=True, 
          save_to=None):
    
    #Logging
    format_strs = []
    if verbose: format_strs.append('stdout')
    if save_to: format_strs.append('csv')
    logger.configure(dir=save_to, format_strs=format_strs)

    
    #Learning iteration
    for it in range(max_iterations):
        rho = pol.eval_params() #Higher-order-policy parameters
        if save_to: np.save(save_to + '/weights_' + str(it), rho)
        if verbose>1:
            print('Higher-order parameters:', rho)
            print('Fisher diagonal:', pol.eval_fisher())
            #print('Renyi:', pol.renyi(pol))
            
        #Batch of episodes
        actor_params = []
        rets, disc_rets, lens = [], [], []
        for ep in range(batch_size):
            #Initialize actor
            theta = pol.resample() #Sample actor parameters
            actor_params.append(theta)
            
            #Run episode
            ret, disc_ret, ep_len = eval_trajectory(env, pol, gamma, task_horizon, feature_fun)
            rets.append(ret)
            disc_rets.append(disc_ret)
            lens.append(ep_len)
        
        
        logger.log('\n********** Iteration %i ************' % it)
        logger.record_tabular('AvgRet', np.mean(rets))
        logger.record_tabular('J', np.mean(disc_rets))
        logger.record_tabular('VarJ', np.var(disc_rets, ddof=1)/batch_size)
        logger.record_tabular('BatchSize', batch_size)
        logger.record_tabular('AvgEpLen', np.mean(lens))
        
        #Update higher-order policy
        grad = pol.eval_gradient(actor_params, disc_rets, use_baseline=use_baseline)
        grad2norm = np.linalg.norm(grad, 2)
        step_size_it = {'const': step_size,
                        'norm': step_size/grad2norm if grad2norm>0 else 0,
                        'vanish': step_size/np.sqrt(it+1)
                }.get(step_size_strategy, step_size)
        delta_rho = step_size_it * grad
        pol.set_params(rho + delta_rho)
        
        logger.record_tabular('StepSize', step_size_it)
        logger.record_tabular('GradInftyNorm', np.linalg.norm(grad, np.infty))
        logger.record_tabular('Grad2Norm', grad2norm) 
        logger.dump_tabular()
        
    