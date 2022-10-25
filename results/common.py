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
