#!/usr/bin/env python3

import matplotlib.pyplot as plt

from common import *

plt.figure(figsize=(10, 8))

ax1 = plt.subplot(221)
data = read_data('base/sharded-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='Sharded: Receive Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax1,
)

ax2 = plt.subplot(222, sharex=ax1, sharey=ax1)
data = read_data('base/singleton-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='Singleton: Receive Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax2,
)

plt.ylim(bottom=0)

ax3 = plt.subplot(223)
data = read_data('base/sharded-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='Sharded: Transmit Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax3,
)

ax4 = plt.subplot(224, sharex=ax3, sharey=ax3)
data = read_data('base/singleton-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='Singleton: Transmit Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax4,
)

plt.ylim(bottom=0)
# plt.suptitle('Network Bandwidth per Pod', weight='bold')
plt.savefig('base-network.pdf', bbox_inches='tight')
