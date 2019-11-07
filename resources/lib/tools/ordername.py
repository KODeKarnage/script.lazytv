import xbmc

def order_name(raw_name):
    """ changes the raw name into an orderable name,
		removes 'The' and 'A' in a bunch of different languages"""

    name = raw_name.lower()
    language = xbmc.getInfoLabel("System.Language")

    if language in ["English", "Russian", "Polish", "Turkish"] or "English" in language:
        if name.startswith("the "):
            new_name = name[4:]
        else:
            new_name = name

    elif language == "Spanish":
        variants = ["la ", "los ", "las ", "el ", "lo "]
        for v in variants:
            if name.startswith(v):
                new_name = name[len(v) :]
            else:
                new_name = name

    elif language == "Dutch":
        variants = ["de ", "het "]
        for v in variants:
            if name.startswith(v):
                new_name = name[len(v) :]
            else:
                new_name = name

    elif language in ["Danish", "Swedish"]:
        variants = ["de ", "det ", "den "]
        for v in variants:
            if name.startswith(v):
                new_name = name[len(v) :]
            else:
                new_name = name

    elif language in ["German", "Afrikaans"]:
        variants = ["die ", "der ", "den ", "das "]
        for v in variants:
            if name.startswith(v):
                new_name = name[len(v) :]
            else:
                new_name = name

    elif language == "French":
        variants = ["les ", "la ", "le "]
        for v in variants:
            if name.startswith(v):
                new_name = name[len(v) :]
            else:
                new_name = name

    else:
        new_name = name

    return new_name