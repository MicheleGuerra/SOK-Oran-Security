#!/usr/bin/env python

import pandas as pd

file = "../data/government.csv"

df = pd.read_csv(file).dropna(axis=0, subset="Name", how="all")

if __name__ == "__main__":
    print(df)
