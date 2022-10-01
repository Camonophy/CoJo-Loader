import json
import string


def getJSONFile(path: string = ".") -> dict[string: string]:
    data = {}
    try:
        with open(path, 'r') as file:
            data = json.load(file)
    except: pass

    return data
