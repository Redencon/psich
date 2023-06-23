import json


class User:
    def __init__(self, number, name, last_message):
        """
        Initializes the User object with the data.

        @param number - The number of the message that was sent.
        @param name - The username of the User.
        @param last_message - id of the last message that was sent
        """
        self.number = number
        self.name = name
        self.last_message = last_message

    def to_dict(self):
        """
        Converts the object to a dictionary.

        This is used for serialization and deserialization.

        @return The object serialized to a dictionary with the following keys:
           number : The number of the message.
           name : The username of the User.
           last_message : The last message id
        """
        return {
            "number": self.number,
            "name": self.name,
            "last_message": self.last_message,
        }


class UserStorage:
    def __init__(self, filename):
        """
        Initialize the UserStorage object.

        This is called by __init__ and should not be called directly.

        The file is loaded from disk and the users list is cleared

        @param filename - Name of the file to
        """
        self.filename = filename
        self.users = []
        self.load()

    def add_user(self, user):
        """
        Add a user to the list of users.

        @param user - The user to add to the list of users
        """
        self.users.append(user)
        self.save()

    def remove_user(self, user):
        """
        Remove a user from the list of users.

        This is a destructive action. The user will no longer be able access bot

        @param user - The user to remove
        """
        self.users.remove(user)
        self.save()

    def save(self):
        """
        Save the list of users to a json file
        """
        with open(self.filename, "w") as f:
            users_dict = [user.to_dict() for user in self.users]
            json.dump(users_dict, f)

    def load(self):
        """
        Load users from file and create a file if it doesn't exist
        """
        try:
            with open(self.filename, "r") as f:
                users_dict = json.load(f)
                self.users = [User(**user_dict) for user_dict in users_dict]
        except FileNotFoundError:
            self.users = []
            self.save()
