import os
import json

A = ["responses", "responses2"]
for foldername in A:
    for el in os.listdir(os.getcwd() + "/" + foldername):
        with open(foldername + "/" + el, "r", encoding="utf-8") as file:
            data = json.load(file)
        data["responses"]["2023/4/3"] = 2
        with open(foldername + "/" + el, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
