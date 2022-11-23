#!/usr/bin/env python3

import matplotlib.pyplot as plt

from common import *

plt.figure(figsize=(10, 5))

ax1 = plt.subplot(121)
data = read_data('base/sharded-cpu.csv')
data.plot(
    title='Sharded',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ax=ax1,
)

ax2 = plt.subplot(122, sharex=ax1, sharey=ax1)
data = read_data('base/singleton-cpu.csv')
data.plot(
    title='Singleton',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ax=ax2,
)

plt.ylim(bottom=0)
# plt.suptitle('CPU Usage per Pod', weight='bold')
plt.savefig('base-cpu.pdf', bbox_inches='tight')
