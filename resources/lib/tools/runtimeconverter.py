

def runtime_converter(time_string):
    if time_string == "":
        return 0
    else:
        x = time_string.count(":")

        if x == 0:
            return int(time_string)
        elif x == 2:
            h, m, s = time_string.split(":")
            return int(h) * 3600 + int(m) * 60 + int(s)
        elif x == 1:
            m, s = time_string.split(":")
            return int(m) * 60 + int(s)
        else:
            return 0

