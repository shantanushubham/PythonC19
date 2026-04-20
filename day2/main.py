# from utils.file_util import read_txt, write_to_file, read_json, write_to_json, read_csv
from utils.file_util import read_csv
from utils.math_util import divide

# content = read_txt("./files/text.txt")
# print(content)

# write_to_file("./files/output.txt", content + "\nToday is Feb 28")

# users = read_json("./files/users.json")
# users.append({
#   "name": "Rob",
#   "age": 23,
#   "email": "rob@gmail.com"
# })
# print(users)

# write_to_json("./files/users.json", users)

#write to csv
# to_write = [
#   {"name": "Shantanu", "age": 23},
#   {"name": "Aman", "age": 22},
#   {"name": "Riya", "age": 21}
# ]
# write_to_csv("./files/shantanu.csv", to_write)

try: # Doubtful Code that can throw the exception
  # read_csv("./files/shantanu.csv")
  divide(10, 0)
  # print(ans)
except FileNotFoundError: # How to handle the exception
  print("Error occurred")
except ZeroDivisionError:
  print("Dont use 0")
  try:
    divide(10, 0)
  except:
    print("Inside Nested Except")
finally:
  print("Hello World")