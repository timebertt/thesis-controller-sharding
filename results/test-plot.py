#!/usr/bin/env python3

import matplotlib.pyplot as plt
import pandas as pd

# read data
data = pd.read_csv(
    "test-plot.csv",
    parse_dates=["ts"],
    date_parser=lambda col: pd.to_datetime(col, utc=True, unit="s"),
)

plt.figure(figsize=(10, 6))

for controller in data.controller.unique():
    controller_data = data[data.controller.eq(controller)]
    min_ts = controller_data.ts.min()

    plt.plot((controller_data.ts - min_ts).astype("timedelta64[s]"), controller_data.value, label=controller)

plt.title("Reconciliation Rate by Controller")
plt.grid(True)
plt.xlabel('Time in seconds')
plt.ylabel('ops/s')
plt.xlim([0, (data.ts.max() - data.ts.min()).seconds])
plt.legend(loc="best")

# export
plt.savefig('test.pdf', bbox_inches="tight")
