#!/usr/bin/env python

import pandas as pd

threats_file = "../data/threats.csv"
risks_file = "../data/risks.csv"

replacements = {
    "\n": " ",
    "ML components deploying machine learning (xApps, rApps)": "ML components deploying machine learning (xApps/rApps)",
    "(xApps/rApps),Near-RT-RIC SW": "(xApps/rApps), Near-RT-RIC SW",
    "ML prediction results,A1 policies,E2 node data": "ML prediction results, A1 policies, E2 node data",
    "ML prediction results ,Data transported over the O1 interface,A1 policies": "ML prediction results, Data transported over the O1 interface, A1 policies",
    "Non-RT-RIC SW .": "Non-RT-RIC SW",
}

threats_df = pd.read_csv(threats_file)
for key, value in replacements.items():
    threats_df["Affected Components"] = threats_df["Affected Components"].str.replace(
        key, value, regex=False
    )

# # print all instances of "ML components deploying machine learning'"
# ml_instances = threats_df[
#     threats_df["Affected Components"].str.contains(
#         "ML components deploying machine learning", na=False
#     )
# ]
# for index, row in ml_instances.iterrows():
#     print(f"Row {index}: {row['Affected Components']}")

risks_df = (
    pd.read_csv(risks_file)
    # spec typos
    .replace(
        {
            "T-ORAN-10": "T-O-RAN-10",
        }
    )
    # drop Threat ID == 'T-TS-01'
    .query("`Risk ID` != 'T-TS-01'")
    # fill CIA NA with empty string
    .fillna({"CIA": ""})
    .assign(Confidentiality=lambda x: x["CIA"].str.contains("C"))
    .assign(Integrity=lambda x: x["CIA"].str.contains("I"))
    .assign(Availability=lambda x: x["CIA"].str.contains("A"))
)

# print where confidentiality is na
na = risks_df[risks_df["Confidentiality"].isna()]
assert len(na) == 0

# left-join to add threat component info to risks_df
df = pd.merge(
    risks_df, threats_df, left_on="Threat Key", right_on="Threat ID", how="left"
)

# Find the rows where the Threat Key is not found in the Threat ID
not_found = df[df["Threat ID"].isnull()]
assert len(not_found) == 0

df = df.drop(columns=["Threat ID", "Threat Key"], axis=1)


if __name__ == "__main__":
    print(df)
