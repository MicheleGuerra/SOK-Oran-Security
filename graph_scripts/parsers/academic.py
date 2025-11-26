#!/usr/bin/env python

import pandas as pd

file = "../data/academic.csv"

df = pd.read_csv(file)

df_attacks = (
    df.query("`Type` == 'Attack'")
    .query("`Reference` != 'This Work'")
    .reset_index(drop=True)
)
df_our_attacks = (
    df.query("`Type` == 'Attack'")
    .query("`Reference` == 'This Work'")
    .reset_index(drop=True)
)
df_preventative = df.query("`Type` == 'Preventative Measure'").reset_index(drop=True)
df_defenses = df.query("`Type` == 'Defense'").reset_index(drop=True)

if __name__ == "__main__":
    print(df_attacks)
    print(df_our_attacks)
    print(df_preventative)
    print(df_defenses)
