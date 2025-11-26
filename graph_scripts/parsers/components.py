#!/usr/bin/env python

import pandas as pd

file = "../data/components.csv"

df = pd.read_csv(file)

if __name__ == "__main__":
    print(df)
