import json
import os

with open("SaveFile.decrypted (10).txt", "r") as file:
    lines = file.readlines()

# NewLevel
index = lines[998].index(":") + 2
lines[998] = lines[998][:index] + "101\n"

for i in range(8, 20):
    # Prestige
    index = lines[566].index(":") + 2
    lines[566] = lines[566][:index] + f"{i}\n"
    # PrestigeIndex
    index = lines[1002].index(":") + 2
    lines[1002] = lines[1002][:index] + f"{i}\n"
    with open(f"phas_output/SaveFile_{i}_decrypted.txt", "w") as file:
        file.writelines(lines)
