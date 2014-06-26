import json

def save_json(data, filename):
    with open(filename, 'w') as file:
        file.write(json.dumps(data, indent=4))

def load_json(path):
    with open(path) as file:
        return json.loads(file.read())
