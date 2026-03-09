import json
import csv


def read_txt(file_path):
  # lines = list()
  content = None
  with open(file_path, "r") as file:
    content = file.read()
    # for line in file:
    #   lines.append(line.strip())
  
  return content

def write_to_file(file_path, to_write):
  with open(file_path, "w") as file:
    file.write(to_write)

def read_json(file_path):
  with open(file_path, 'r') as file:
    users = json.loads(file.read())

  return users

def write_to_json(file_path, to_write):
  with open(file_path, "w") as file:
    json.dump(to_write, file)

def read_csv(file_path):
  with open(file_path, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
      print(row['name'])

def write_to_csv(file_path, to_write):
  with open(file_path, 'w', newline='') as file:
    fieldnames = ['name', 'age']
    writer = csv.DictWriter(file, fieldnames=fieldnames)

    writer.writeheader()
    for row in to_write:
      writer.writerow(row)
