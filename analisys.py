import os
import json
from datetime import datetime
import matplotlib.pyplot as plt

folder_path = 'responses/'
current_date = datetime.today().strftime('%Y/%m/%d')

year = 2023
month = 3
plt.figure(figsize=(12, 8))
a = [None]*31
for i in range(1, 32):
    count = 0
    total = 0
    cur = str(year)+'/'+str(month)+'/'+str(i)
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            with open(os.path.join(folder_path, filename), 'r') as f:
                data = json.load(f)
                if 'responses' in data and cur in data['responses']:
                    count += 1
                    total += data['responses'][cur]
    if count > 0:
        a[i-1] = total/count
print(a)
plt.plot(a)
plt.gca().invert_yaxis()
plt.show()

if count > 0:
    average = total / count
else:
    average = 0

print(f'Count: {count}')
print(f'Average: {average}')