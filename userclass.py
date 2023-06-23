import json


class User:
    def __init__(self, number, name, last_message):
        self.number = number
        self.name = name
        self.last_message = last_message

    def to_dict(self):
        return {
            "number": self.number,
            "name": self.name,
            "last_message": self.last_message,
        }


class UserStorage:
    def __init__(self, filename):
        self.filename = filename
        self.users = []
        self.load()

    def add_user(self, user):
        self.users.append(user)
        self.save()

    def remove_user(self, user):
        self.users.remove(user)
        self.save()

    def save(self):
        with open(self.filename, "w") as f:
            users_dict = [user.to_dict() for user in self.users]
            json.dump(users_dict, f)

    def load(self):
        try:
            with open(self.filename, "r") as f:
                users_dict = json.load(f)
                self.users = [User(**user_dict) for user_dict in users_dict]
        except FileNotFoundError:
            self.users = []
            self.save()
