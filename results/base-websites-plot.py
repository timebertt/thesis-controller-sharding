#!/usr/bin/env python3

import matplotlib.pyplot as plt

from common import *

plt.figure(figsize=(10, 6))

ax1 = plt.subplot(121)
data = read_data('base/sharded-websites_per_project.csv')
data.plot(
    title='Websites per Project (stacked)',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Website count',
    xlim=[0, data.index.max()],
    kind='area',
    ax=ax1,
)
plt.ylim(bottom=0)

ax2 = plt.subplot(122)
data = read_data('base/sharded-websites_per_shard.csv')
data.plot(
    title='Websites per Shard',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    xlim=[0, data.index.max()],
    ax=ax2,
)
plt.ylim(bottom=0)

plt.savefig('base-websites.pdf', bbox_inches='tight')
