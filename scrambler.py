import random

with open("text.txt", "r", encoding="utf-8") as file:
    for line in file.readlines():
        lin = []
        for word in line.split():
            if len(word) < 4:
                lin += [word]
                continue
            li = list(word)
            b = li[1:-1]
            random.shuffle(b)
            lin += [li[0] + "".join(b) + li[-1]]
        print(" ".join(lin))
