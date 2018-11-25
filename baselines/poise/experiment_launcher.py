from baselines.poise import run
#
# import sys
# import os
# import numpy as np
# import warnings
# import time
# import random
from joblib import Parallel, delayed
# sys.path.append('..')


def frange(start, stop, step):
    i = start
    while i < stop:
        yield i
        i += step


if __name__ == '__main__':
    args = []
    for i in frange(0.1, 0.2, 0.1):
        for j in range(3):
            args.append([str(i), str(j)])

    n_jobs = len(args)
    Parallel(n_jobs=n_jobs)(delayed(run.main)(
        ['--delta', args[i][0],
         '--seed', args[i][1],
         '--bounded_policy', 'True',
         '--file_name', 'progress'
         ]
        ) for i in range(n_jobs))
