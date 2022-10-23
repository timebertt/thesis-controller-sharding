import matplotlib.pyplot as plt
import pandas as pd


def read_data(filename):
    data = pd.read_csv(
        filename,
        parse_dates=['ts'],
        date_parser=lambda col: pd.to_datetime(col, utc=True, unit='s'),
    )
    ts_min = data.ts.min()
    data.ts = (data.ts - ts_min).astype('timedelta64[s]')
    return data.pivot(index='ts', columns=data.columns.drop(labels=['ts', 'value']), values='value')


def plot_websites_per_project(data):
    for project in data.namespace.unique():
        d = data[data.namespace.eq(project)]
        plt.plot(d.ts, d.value, label=project)

    plt.title('Websites per Project')
    plt.grid(True)
    plt.xlabel('Time in seconds')
    plt.ylabel('Website count')
    plt.xlim([0, data.ts.max()])
    plt.legend(loc='best')


def plot_websites_per_shard(data):
    for shard in data.shard.unique():
        d = data[data.shard.eq(shard)]
        plt.plot(d.ts, d.value, label=shard)

    plt.title('Websites per Shard')
    plt.grid(True)
    plt.xlabel('Time in seconds')
    plt.ylabel('Website count')
    plt.xlim([0, data.ts.max()])
    plt.legend(loc='best')
