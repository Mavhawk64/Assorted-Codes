import os

file_path = os.path.join(os.path.dirname(__file__), "missing_spaces.txt")
output_file_path = os.path.join(os.path.dirname(__file__), "output.txt")

with open(file_path, "r") as file:
    data = file.read()

# if data is immediately followed by \ni_tm = ..., we need to add \n between
# 1.23E+2\ni_tm = 5 -> 1.23E+2\n\ni_tm = 5 but 1.23E+2\n\ni_tm = 5 stays same
data = data.replace("\n\ni_tm", "\ni_tm")
data = data.replace("\ni_tm", "\n\ni_tm")

with open(output_file_path, "w") as file:
    file.write(data)
