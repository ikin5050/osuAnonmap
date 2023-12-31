import json

try:
	import pandas as pd
	pandas_imported = True
except ImportError:
	pandas_imported = False


def from_json(text_json, type_return: str):
	"""A function to convert json result in a type specify."""
	if type_return == 'json':
		return text_json

	if type_return == 'dict':
		return json.loads(text_json)

	if type_return == 'dataframe':
		if pandas_imported:
			return pd.read_json(text_json)
		raise ValueError("type_return can't take 'dataframe' value if pandas is not installed! Install pandas and retry.")
	raise ValueError(f"type_return can't take the value: '{type_return}'. Possibles types: 'json', 'dict', 'dataframe'.")