# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：trans.py
日期：2023年04月28日 17:25
"""
import pandas
import json
df = pandas.read_csv("杭千高速点位信息.csv")

data = {}

for _, row in df.iterrows():
    data.setdefault("hangqian_hiway", {}).setdefault(row["node_id"], {"ip": row["its800_ip"],"is_active": True})

with open("data.json", "w") as f:
    json.dump(data, f, indent=2)
