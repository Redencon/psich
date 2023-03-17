import pickle
import random
import os

class User:
    def __init__(self, id: int, name: str = None):
        self.id = id
        self.roll_pseudonym()
        self.name = name
        self._last_personal_message = 0
        self.last_chat_message = 0
        self.save()
        
    def roll_pseudonym(self):
        parts0 = ['soft', 'cute', 'angry', 'fuzzy', 'toothy', 'stinky', 'warm', 'whiney',
                    'wet', 'sleepy', 'happy', 'loud', 'curious', 'subborn', 'horny', 'rough']
        parts1 = ['cerulean', 'chartreuse', 'fuchsia', 'indigo', 'mauve', 'olive', 'periwinkle',
                    'rust', 'teal', 'turquoise', 'vermilion', 'violet', 'amber', 'burgundy', 'coral',
                    'crimson', 'emerald', 'lavender', 'magenta', 'marigold', 'navy', 'peach', 'rose', 'sapphire']
        parts2 = ['cat', 'dog', 'bird', 'fish', 'flower', 'tree', 'sergull', 'hedgehog',
                    'greninja', 'xenomorph', 'cthulhu', 'azathoth', 'protogen', 'imp', 'derg',
                    'phoenix', 'ouroboros', 'salamander', 'fox', 'centaurus', 'ditto', 'cerberus',
                    'owl', 'wolf', 'chimera', 'husky', 'collie', 'jaguar', 'panther', 'lion',
                    'eagle', 'jay', 'duck', 'jakal', 'axolotl']
        self.pseudonym = random.choice(parts0) + ' ' + random.choice(parts1) + ' ' + random.choice(parts2)
        self.save()
        return
    
    def save(self):
        filename = f'users/user_{self.id}.bin'
        with open(filename, 'wb') as f:
            data = pickle.dumps(self)
            f.write(data)

    @property
    def last_personal_message(self):
        return self._last_personal_message

    @last_personal_message.setter
    def last_personal_message(self, id: int):
        self._last_personal_message = id
        self.save()
    
    @staticmethod
    def load(id = None, filename = None):
        if id is None and filename is None:
            return None
        if filename is None:
            filename = f'users/user_{id}.bin'
        with open(filename, 'rb') as f:
            data = f.read()
            user = pickle.loads(data)
            return user


class UserManager:
    USERLIMIT = 1000

    def __init__(self):
        self.users = {}
        self.load_all_users()
        return
    
    def add_user(self, user: User):
        self.users[user.id] = user
    
    def new_user(self, id, name):
        if len(self.users) > UserManager.USERLIMIT:
            return None
        new_user = User(id, name)
        while self.get_user_by_pseudonym(new_user.pseudonym) is not None:
            new_user.roll_pseudonym()
        self.users[id] = new_user
        return new_user
    
    def get_user_by_id(self, id: int) -> User:
        if id in self.users:
            return self.users[id]
        else:
            return None
    
    def get_user_by_pseudonym(self, pseudonym) -> User:
        for user in self.users.values():
            if user.pseudonym == pseudonym:
                return user
        return None
    
    def delete_user(self, id):
        if id in self.users:
            filename = f'user_{id}.bin'
            if os.path.exists(filename):
                os.remove(filename)
            del self.users[id]
    
    def save_all_users(self):
        for user in self.users.values():
            user.save()
    
    def load_all_users(self):
        A = ['users/' + el for el in os.listdir(os.getcwd()+'/users')]
        for filename in A:
            num = int(filename[11:-4])
            self.users[num] = User.load(filename=filename)
        return
