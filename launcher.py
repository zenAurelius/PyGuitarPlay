from tkinter import filedialog
from tkinter import Tk
import os
import json
import start

root = Tk()
root.filename = filedialog.askopenfilename(initialdir="./songbook", title="Select file", filetypes=(("guitar", "*.gp5"), ("all files", "*.*")))
with open('params.json') as json_file:
    params = json.load(json_file)

params['file'] = os.path.basename(os.path.normpath(root.filename))
with open('params.json', 'w') as outfile:
    json.dump(params, outfile)
root.destroy()
s = start.Guitarician()
s.start()
