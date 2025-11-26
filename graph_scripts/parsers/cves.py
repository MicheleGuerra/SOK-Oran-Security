#!/usr/bin/env python

import pandas as pd

file = "../data/cves.csv"

df = pd.read_csv(file).dropna(subset=["Date Published"])

if __name__ == "__main__":
    print(df)
