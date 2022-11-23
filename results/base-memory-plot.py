#!/usr/bin/env python3

import matplotlib.pyplot as plt

from common import *

plt.figure(figsize=(10, 5))

ax1 = plt.subplot(121)
data = read_data('base/sharded-memory.csv')
data = data / (2 ** 20)
data.plot(
    title='Sharded',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Memory usage in MiB',
    xlim=[0, data.index.max()],
    ax=ax1,
)

ax2 = plt.subplot(122, sharex=ax1, sharey=ax1)
data = read_data('base/singleton-memory.csv')
data = data / (2 ** 20)
data.plot(
    title='Singleton',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Memory usage in MiB',
    xlim=[0, data.index.max()],
    ax=ax2,
)

plt.ylim(bottom=0)
# plt.suptitle('Memory Usage per Pod', weight='bold')
plt.savefig('base-memory.pdf', bbox_inches='tight')
