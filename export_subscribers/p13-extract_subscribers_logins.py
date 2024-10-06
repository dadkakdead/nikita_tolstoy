from os import listdir
from os.path import isfile, join

def get_username_from_text_string(x):
    token = "username='"
    p1 = x.find(token)
    if p1 == -1:
#         print(x)
        return None
    else:
        p2 = x.find("'", p1+len(token))
        return x[p1+len(token):p2]

mypath = "./"
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f)) and f.endswith(".txt") and f.startswith("filename_subscribers_")]

# print(onlyfiles)

users = []

for fn in sorted(onlyfiles):
    with open(mypath+fn, "r") as f:
        c = f.read().splitlines()
        users.extend(c)
        # print("%s: %d" % (fn.replace("filename_subscribers_", "").split("_")[0], len(c)))

uu = list(users)

uu_usernames = list(map(lambda x: get_username_from_text_string(x), uu))
uu_usernames = [x for x in uu_usernames if x is not None]
uu_usernames = list(set(uu_usernames))
print(len(uu_usernames))

import sys
original_stdout = sys.stdout

with open('OUTPUT_subscribers.txt', 'w') as f:
    sys.stdout = f
    for u in uu_usernames:
        print(u)
    sys.stdout = original_stdout