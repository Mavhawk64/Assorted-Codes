import os

file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materials.txt")


def open_url(url: str) -> None:
    """Open a URL in the default web browser."""
    import webbrowser

    webbrowser.open(url)


with open(file_path, "r", encoding="utf-8") as file:
    materials = [
        line.strip()
        for line in file
        if line.strip() and ":" not in line and "--- IGNORE ---" not in line
    ]
    matdict = {}
    for material in materials:
        mat = material.split("(")[0].strip()
        num = int(mat[: mat.find(" ")])
        mat = mat[mat.find(" ") :].strip()
        if mat not in matdict:
            matdict[mat] = 0
        matdict[mat] += num

# print(matdict)

url = "https://resourcecalculator.com/minecraft/#"

for key in matdict:
    url += f"{key.replace(' ', '')}={matdict[key]}&"
    # open_url(url[:-1])
    # print("\n\n")

url = url[:-1]
print(url)
open_url(url)

print("\n\n")

# print(len(matdict.keys()))
# sorted_keys = sorted(matdict.keys())
# for key in sorted_keys:
#     print(key)
