import os
import json
import responses
import gpt_users

manager = gpt_users.UserManager()

for folder in ('responses', 'responses2'):
  new_folder = '{}_n'.format(folder)
  if not os.path.exists(new_folder):
    os.mkdir(new_folder)
  for file in os.listdir(folder):
    with open(os.path.join(folder, file)) as f:
      data = json.load(f)
    responses.User.parse_old_data(
      data, int(file[:-5]), manager
    ).dump(new_folder)
