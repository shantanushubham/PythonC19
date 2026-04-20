# first_num = int(input("First Number: "))
# second_num = int(input("Second Number: "))
# HELLO = 'Hello'
# print(HELLO)
# print(first_num + second_num)
# print('World')

# Data Structres in Python
# int arr[] = new arr[5]
import copy

arr = [10, 20, 30, 40]
names = ["Shantanu", "Aman", "Riya"]
mixed = [10, "hello", False, 3.14]
empty = []

# print(arr[1:4]) # slicing in python [start, end)
# print(arr[:3]) # slicing in python
# print(arr[2:]) 

# arr[3] = 41
# print(arr)

# arr.append(50)
# arr.insert(3, 35)
# print(arr)
# arr.remove(20)
# print(arr)

# arr.pop()
# arr.pop(1) # remove at index
# arr.sort()
# arr.reverse()
# print(arr)

# for (int i = 0; i < arr.length; i++) {
#   System.out.println(arr[i]);
# }

# for i in range(len(arr)):
#   print(arr[i])

# for n in arr:
#   print(n)

# brr = arr # shallow copying (pass by reference)
# brr = arr.copy() # deep copying (for primitive types 1D array)
# crr = [1,2,3] # 1D
# crr = [[1,2], [2,3], [3,4]] # 2D
# brr[1] = 0
# print(arr)
# print(brr)

# numbers = [[1, 2], [2, 3]]
# numbers_copy = numbers.copy() # it created a new array which contains old elements

# # [[100, 2]][[2, 3]][[1,2]][[2,3]][][][][][] -> Computer Memory
# #    x1      x2        x5     x6
# # numbers = [&x1, &x2] -> x3

# # numbers_copy = create a new array but the same arrays inside [&x5, &x6] -> x4


# print(numbers)
# numbers_copy = copy.deepcopy(numbers) We need copy module to do deep copy for 2D arrays or nested arrays(import copy)
# print(numbers_copy)

# numbers[0][0] = 100

# print(numbers)
# print(numbers_copy)

# Tuples
tple = tuple()
tple = (1, 2, 3)

# Set
my_set = set()
my_set.add('Guava')
my_set.add('Apple')
my_set.add('Dragonfruit')
my_set.add('Apple')
print(my_set)

# Dict or Dictionary
# 1->Rahul
# 2->Ujwal
# 3->Ashutosh

my_dict = { # Key -> Value Pair
  1: "Rahul",
  2: "Ujwal",
  3: "Ashutosh",
  'a': "AirTribe"
}

for key in my_dict.keys():
  print(my_dict[key])
print("*********")
for value in my_dict.values():
  print(value)
print("*********")
for (key, value) in my_dict.items():
  print(str(key) + "->" + value)

# Homework:
# 1. Learn Lists, Tuples and Sets
# 2. Learn Dict
# 3. Learn about Functions

