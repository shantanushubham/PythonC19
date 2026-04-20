# What are the things that you need in order to make a car?
# 1. Engine
# 2. Wheels
# 3. Color
# 4. Chassis
# 5. Headlights

# Car1 - is a car from car-idea
# Car2 - is a car from car-idea

# Class is a blueprint
# class Pair:

#   part_one: int
#   part_two: str

# name: str = "Shantanu"
# my_pair = Pair()


class Building:

    # Significant
    def __init__(self, no_of_floors: int, color: str):
        self.no_of_floors = no_of_floors
        self.color = color

    def to_string(self):
      print(self.no_of_floors, self.color)


# my_building_1 is an object of the class Building
my_building_1 = Building(no_of_floors=10, color="Yellow")
# print(my_building_1.color)

# my_building_2 is an object of the class Building
my_building_2 = Building()

print(my_building_1, my_building_2)
