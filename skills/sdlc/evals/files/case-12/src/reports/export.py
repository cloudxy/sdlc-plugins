import pandas as pd


def export_monthly(path_glob, out_csv):
    # 40 s on the 2026-09 data: reads ~180 CSV files, then groups by tenant
    frames = [pd.read_csv(p) for p in sorted(__import__("glob").glob(path_glob))]
    df = pd.concat(frames)
    df.groupby(["tenant_id", "month"]).agg(total=("amount", "sum")).to_csv(out_csv)
