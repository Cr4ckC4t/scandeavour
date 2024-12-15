from os import listdir
from os.path import isfile, join, basename, dirname, abspath

directory = dirname(abspath(__file__))

__all__ = [
	f[:-3] # remove the .py
	for f in listdir(directory) # list the ingestors folder
	if isfile(join(directory, f)) and f.endswith('.py') and '__init__' not in f # ensure it ends with .py
]
