import os
import json

folder_path = 'responses/'
current_date = '2023/3/8'
count = 0
total = 0

for filename in os.listdir(folder_path):
    if filename.endswith('.json'):
        with open(os.path.join(folder_path, filename), 'r') as f:
            data = json.load(f)
            if 'responses' in data and current_date in data['responses']:
                count += 1
                total += data['responses'][current_date]

if count > 0:
    average = total / count
else:
    average = 0

print(f'Count: {count}')
print(f'Average: {average}')