import os
import json

def make_report(foldername: str, filename: str = 'report.json'):
    final = {}
    for el in os.listdir(os.getcwd()+foldername):
        with open(foldername + '/' + el, 'r', encoding='utf-8') as file:
            data = json.load(file)
        final[el] = data
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(final, file, indent=4, ensure_ascii=False)
    return filename