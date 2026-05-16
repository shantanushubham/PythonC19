def add_two_numbers(a, b):
  if (a < 0 or b < 0):
    raise Exception('Numbers have to be positive')
  if (a > 50 or b > 50):
    return 0
  return a + b


sum = add_two_numbers(5, 6)
print(sum)
# If sum = 11, then add_two_numbers is working fine
# Otherwise, there is a problem in add_two_numbers