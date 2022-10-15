#!/usr/bin/env python3

import matplotlib.pyplot as plt
import pandas as pd

# do subplots side by side
plt.figure(figsize=(10,6))

# subplot per project
plt.subplot(121)

# read data
data = pd.read_csv(
    "test-websites_per_project.csv",
    parse_dates=["ts"],
    date_parser=lambda col: pd.to_datetime(col, utc=True, unit="s"),
)
ts_min = data.ts.min()

for project in data.namespace.unique():
    d = data[data.namespace.eq(project)]
    plt.plot((d.ts - ts_min).astype("timedelta64[s]"), d.value, label=project)

plt.title("Websites per Project")
plt.grid(True)
plt.xlabel('Time in seconds')
plt.ylabel('count')
plt.xlim([0, (data.ts.max() - data.ts.min()).seconds])
plt.legend(loc="best")

# subplot per shard
plt.subplot(122)

# read data
data = pd.read_csv(
    "test-websites_per_shard.csv",
    parse_dates=["ts"],
    date_parser=lambda col: pd.to_datetime(col, utc=True, unit="s"),
)
ts_min = data.ts.min()

for shard in data.shard.unique():
    d = data[data.shard.eq(shard)]
    plt.plot((d.ts - ts_min).astype("timedelta64[s]"), d.value, label=shard)

plt.title("Websites per Shard")
plt.grid(True)
plt.xlabel('Time in seconds')
plt.ylabel('count')
plt.xlim([0, (data.ts.max() - data.ts.min()).seconds])
plt.legend(loc="best")

# spacing
plt.subplots_adjust(top=0.92, bottom=0.08, left=0.10, right=0.95, hspace=0.2, wspace=0.3)

# export
plt.savefig('test.pdf', bbox_inches="tight")
