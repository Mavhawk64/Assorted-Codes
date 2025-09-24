import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.bcolors import bcolors  # type: ignore

print("\n\n")

path1 = os.path.dirname(os.path.abspath(__file__))
path2 = os.path.dirname(path1)
print(bcolors.OKBLUE + path1 + bcolors.ENDC)
print(bcolors.OKGREEN + path2 + bcolors.ENDC)

print("\n\n")