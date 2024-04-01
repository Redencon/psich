"""Making burger

by Redencon
"""

from time import sleep

class Plate:
  def __init__(self) -> None:
    self.on_plate: list[str] = []

  def put(self, what: str):
    print(f"I put {what} on the plate.")
    self.on_plate.append(what)
    sleep(2)

  def present(self):
    print("Dish ready!\n\n{}\nPlate".format("\n".join(self.on_plate[::-1])))
    _ = input()


class Patty:
  def __init__(self, meat: str) -> None:
    self.meat = meat
    self.state = "raw"

  def roast(self, time: int):
    if self.state != "raw":
      self.state = "burned"
      return
    if time < 2:
      self.state = "heated"
    elif time < 4:
      self.state = "rare"
    elif time < 5:
      self.state = "medium-rare"
    elif time < 6:
      self.state = "medium"
    elif time < 8:
      self.state = "well-done"
    else:
      self.state = "burned"
    print("Roasting the patty for {} minutes.".format(time))
    for _ in range(3):
      print(".", end="")
      sleep(5)
    print("\nNow patty is {}".format(self.state))
    sleep(1)

  def get(self):
    return "{} {} patty".format(self.state, self.meat)

  
class Burger:
  def __init__(self, plate: Plate) -> None:
    self.plate = plate
    plate.put("bottom bun")
    plate.put("ketchup")
    patty = Patty("beef")
    patty.roast(5)
    plate.put(patty.get())
    plate.put("tomato")
    plate.put("onions")
    plate.put("pickles")
    plate.put("ranch sauce")
    plate.put("top bun")


if __name__ == "__main__":
  plate = Plate()
  Burger(plate)
  plate.present()
