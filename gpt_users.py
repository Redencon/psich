import pickle
import random
import os


class User:
    def __init__(self, id: int, name: str = None):
        """
        Initializes a pseudonym with the given id and name.
        This is the first step in the creation process.

        :param: id - The id of the pseudonym. This should be unique among all users.
        :param: name - The name of the pseudonym. This should be unique among all users
        """
        self.id = id
        self.roll_pseudonym()
        self.name = name
        self._last_personal_message = 0
        self.last_chat_message = 0
        self.save()

    def roll_pseudonym(self):
        """Generate a random pseudonym"""
        parts0 = [
            "soft",
            "cute",
            "angry",
            "fuzzy",
            "toothy",
            "stinky",
            "warm",
            "whiney",
            "wet",
            "sleepy",
            "happy",
            "loud",
            "curious",
            "subborn",
            "horny",
            "rough",
        ]
        parts1 = [
            "cerulean",
            "chartreuse",
            "fuchsia",
            "indigo",
            "mauve",
            "olive",
            "periwinkle",
            "rust",
            "teal",
            "turquoise",
            "vermilion",
            "violet",
            "amber",
            "burgundy",
            "coral",
            "crimson",
            "emerald",
            "lavender",
            "magenta",
            "marigold",
            "navy",
            "peach",
            "rose",
            "sapphire",
        ]
        parts2 = [
            "cat",
            "dog",
            "bird",
            "fish",
            "flower",
            "tree",
            "sergull",
            "hedgehog",
            "greninja",
            "xenomorph",
            "cthulhu",
            "azathoth",
            "protogen",
            "imp",
            "derg",
            "phoenix",
            "ouroboros",
            "salamander",
            "fox",
            "centaurus",
            "ditto",
            "cerberus",
            "owl",
            "wolf",
            "chimera",
            "husky",
            "collie",
            "jaguar",
            "panther",
            "lion",
            "eagle",
            "jay",
            "duck",
            "jakal",
            "axolotl",
        ]
        self.pseudonym = (
            random.choice(parts0)
            + " "
            + random.choice(parts1)
            + " "
            + random.choice(parts2)
        )
        self.save()
        return

    def save(self):
        """
        Save user data to file
        """
        filename = f"users/user_{self.id}.bin"
        with open(filename, "wb") as f:
            data = pickle.dumps(self)
            f.write(data)

    @property
    def last_personal_message(self) -> int:
        """
        Get the id of last_personal_message of this user

        :return: The last_personal_message of this user
        """
        return self._last_personal_message

    @last_personal_message.setter
    def last_personal_message(self, id: int):
        """
        Set the id of the last personal message.

        :param: id - The id of the message
        """
        self._last_personal_message = id
        self.save()

    @staticmethod
    def load(id: int = None, filename: str = None):
        """
        Load a user from a file

        Either id or filename of user must be provided

        :param: id - The id of the user to load
        :param: filename - The name of the file to load the user from

        :return: The loaded user or None if no user was loaded from disk
        """
        if id is None and filename is None:
            return None
        if filename is None:
            filename = f"users/user_{id}.bin"
        with open(filename, "rb") as f:
            data = f.read()
            user = pickle.loads(data)
            return user


class UserManager:
    USERLIMIT = 1000

    def __init__(self):
        """
        Initialize the class by loading all users

        :return: A dictionary of user objects keyed by user_id (if any)
        """
        self.users = {}
        self.load_all_users()
        return

    def add_user(self, user: User):
        """
        Add a user to the list of users

        :param: user - The user to add to the list of users
        """
        self.users[user.id] = user

    def new_user(self, id, name):
        """
        Create a new user with the given id and name

        :param: id - The id of the user to create. It must be unique.
        :param: name - The name of the user to create. It must be unique.

        :return: The newly created : class : `User` or None
        if there is insufficient space in the user manager
        """
        # Returns None if there are more users than user limit.
        if len(self.users) > UserManager.USERLIMIT:
            return None
        new_user = User(id, name)
        while self.get_user_by_pseudonym(new_user.pseudonym) is not None:
            new_user.roll_pseudonym()
        self.users[id] = new_user
        return new_user

    def get_user_by_id(self, id: int) -> User:
        """
        Get a user by id.

        This is used to check if a user is in the database and if so return it

        :param: id - The id of the user

        :return: The user or None if not in the database
        """
        if id in self.users:
            return self.users[id]
        else:
            return None

    def get_user_by_pseudonym(self, pseudonym) -> User:
        """
        Get a user by pseudonym.

        This is used to check if a user is in the database and if so return it

        :param: pseudonym - The pseudonym of the user

        :return: The user or None if not
        """
        for user in self.users.values():
            if user.pseudonym == pseudonym:
                return user
        return None

    def delete_user(self, id: int):
        """
        Delete a user from the database and delete their file

        :param: id - The id of the user
        """
        if id in self.users:
            filename = f"user_{id}.bin"
            if os.path.exists(filename):
                os.remove(filename)
            del self.users[id]

    def save_all_users(self):
        """
        Save all users in the database

        All users are saved in their respective singular files
        """
        for user in self.users.values():
            user.save()

    def load_all_users(self):
        """
        Load all users from users folder and stores them in UserStorage
        """
        A = ["users/" + el for el in os.listdir(os.getcwd() + "/users")]
        for filename in A:
            num = int(filename[11:-4])
            self.users[num] = User.load(filename=filename)
        return
