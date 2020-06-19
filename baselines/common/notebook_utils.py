#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  1 11:57:26 2018

@author: matteo
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as sts

def bootstrap_ci(x, conf=0.95, resamples=10000):
    means = [np.mean(x[np.random.choice(x.shape[0], size=x.shape[0], replace=True), :], axis=0) for _ in range(resamples)]
    low = np.percentile(means, (1-conf)/2 * 100, axis=0)
    high = np.percentile(means, (1 - (1-conf)/2) * 100, axis=0)
    return low, high
    


def read_data(path, iters=None, default_batchsize=100, scale='Eps'):
    df = pd.read_csv(path, encoding='utf-8')
    if iters: df = df.loc[:iters, :]
    if not 'AvgRet' in df: df['AvgRet'] = df['EpRewMean']
    if not 'EpsThisIter' in df: df['EpsThisIter'] = df['BatchSize'] 
    df['EpsSoFar'] = np.cumsum(df['EpsThisIter'])
    if 'SamplesThisIter' in df: df['SamplesSoFar'] = np.cumsum(df['SamplesThisIter'])
    df['CumAvgRet'] = np.cumsum(df['AvgRet']*df[scale+'ThisIter'])/np.sum(df[scale+'ThisIter'])
    return df

def moments(dfs):
    concat_df = pd.concat(dfs, axis=1)
    mean_df = pd.concat(dfs, axis=1).groupby(by=concat_df.columns, axis=1).mean()
    std_df = pd.concat(dfs, axis=1).groupby(by=concat_df.columns, axis=1).std()
    return mean_df, std_df

def plot_all(dfs, key='AvgRet', ylim=None, scale='Samples'):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    for df in dfs:
        value = df[key]
        ax.plot(df[scale+'SoFar'], value)
    return fig

def plot_ci(dfs, conf=0.95, key='AvgRet', ylim=None, scale='Eps', bootstrap=False, resamples=10000):
    n_runs = len(dfs)
    mean_df, std_df = moments(dfs)
    mean = mean_df[key]
    std = std_df[key]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(mean_df[scale+'SoFar'], mean)
    if bootstrap:
        x = np.array([df[key] for df in dfs])
        interval = bootstrap_ci(x, conf, resamples)
    else:
        interval = sts.t.interval(conf, n_runs-1,loc=mean,scale=std/np.sqrt(n_runs))
    ax.fill_between(mean_df[scale+'SoFar'], interval[0], interval[1], alpha=0.3)
    if ylim: ax.set_ylim(ylim)
    return fig

def compare(candidates, conf=0.95, key='AvgRet', ylim=None, xlim=None, scale='Episodes', bootstrap=False, resamples=10000, roll=1, separate=False, opacity=1):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    entries = []
    if type(roll) is int:
        roll = [roll]*len(candidates)
    for i, candidate_name in enumerate(candidates):
        entries.append(candidate_name)
        dfs = candidates[candidate_name]
        dfs = [dfs[j].rolling(roll[i]).mean() for j in range(len(dfs))]
        n_runs = len(dfs)
        mean_df, std_df = moments(dfs)
        mean = mean_df[key]
        std = std_df[key]
        if not separate:
            ax.plot(mean_df[scale+'SoFar'], mean)   
            if bootstrap:
                x = np.array([df[key] for df in dfs])
                interval = bootstrap_ci(x, conf, resamples)
            else:
                interval = sts.t.interval(conf, n_runs-1,loc=mean,scale=std/np.sqrt(n_runs))
            ax.fill_between(mean_df[scale+'SoFar'], interval[0], interval[1], alpha=0.3)
            print(candidate_name, end=': ')
            print_ci(dfs, conf)
        else:
            for d in dfs:
                ax.plot(d[scale+'SoFar'], d[key], color=colors[i], alpha=opacity)
    ax.legend(entries)
    leg = ax.get_legend()
    if separate:
        for i in range(len(entries)):
            leg.legendHandles[i].set_color(colors[i])
            leg.legendHandles[i].set_alpha(1)
    if ylim: ax.set_ylim(None,ylim)
    if xlim: ax.set_xlim(0,xlim)
    return fig

def plot_data(path, key='VanillaAvgRet'):
    df = pd.read_csv(path)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    mean = df[key]
    ax.plot(df['EpsSoFar'], mean)
    return fig

def print_ci(dfs, conf=0.95, key='CumAvgRet'):
    n_runs = len(dfs)
    mean_df, std_df = moments(dfs)
    total_horizon = np.sum(mean_df['EpLenMean'])
    mean = mean_df[key][len(mean_df)-1]
    std = std_df[key][len(mean_df)-1]
    interval = sts.t.interval(conf, n_runs-1,loc=mean,scale=std/np.sqrt(n_runs))
    print('%f \u00B1 %f\t[%f, %f]\t total horizon: %d' % (mean, std, interval[0], interval[1], int(total_horizon)))