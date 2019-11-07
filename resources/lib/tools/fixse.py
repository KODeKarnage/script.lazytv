
def fix_SE(string):
    if len(str(string)) == 1:
        return "0" + str(string)
    else:
        return str(string)