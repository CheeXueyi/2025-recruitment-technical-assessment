from dataclasses import dataclass
from typing import List, Dict, Union
from flask import Flask, request, jsonify
import re

# ==== Type Definitions, feel free to add or modify ===========================
@dataclass
class CookbookEntry:
	name: str

@dataclass
class RequiredItem():
	name: str
	quantity: int

@dataclass
class Recipe(CookbookEntry):
	required_items: List[RequiredItem]

@dataclass
class Ingredient(CookbookEntry):
	cook_time: int

@dataclass
class ErrorCheckReturn:
	error_occurred: bool
	error_code: Union[int | None]
	error_message: Union[str | None]

@dataclass
class Cookbook:
	recipes: dict
	ingredients: dict

	def __init__(self):
		self.recipes = {}
		self.ingredients = {}


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook = Cookbook()

# Task 1 helper (don't touch)
@app.route("/parse", methods=['POST'])
def parse():
	data = request.get_json()
	recipe_name = data.get('input', '')
	parsed_name = parse_handwriting(recipe_name)
	if parsed_name is None:
		return 'Invalid recipe name', 400
	return jsonify({'msg': parsed_name}), 200

# [TASK 1] ====================================================================
# Removes all characters except letters and whitespace
def remove_illegal_chars(str_to_filter: str) -> str:
	list_of_chars = []
	for char in str_to_filter:
		if char.isalpha() or char == ' ':
			list_of_chars.append(char)
	
	return ''.join(list_of_chars)

# Takes in a recipeName and returns it in a form that 
def parse_handwriting(recipeName: str) -> Union[str | None]:
	# replace hyphens and underscores
	recipeName = recipeName.replace('-', ' ')
	recipeName = recipeName.replace('_', ' ')

	# remove non-letters and non-whitespace characters
	recipeName = remove_illegal_chars(recipeName)

	# convert multiple spaces into single spaces
	words = ' '.join(recipeName.split())
	recipeName = ''.join(words)
	
	# title case each word
	recipeName = recipeName.title()

	if len(recipeName) == 0:
		return None
	else:
		return recipeName


# [TASK 2] ====================================================================
# checks the payload for create_entry POST request for errors
def create_entry_error_check(data: dict) -> ErrorCheckReturn:
	# check type
	if (data['type'] != 'recipe') and (data['type'] != 'ingredient'):
		return ErrorCheckReturn(True, 400, 'type can only be \"recipe\" or \"ingredient\"')

	# check that entry name is unique
	if (data['name'] in cookbook.ingredients) or (data['name'] in cookbook.recipes):
		return ErrorCheckReturn(True, 400, 'Another entry with the same name already exists')
	
	# check cookTime for ingredient
	if (data['type'] == 'ingredient') and (data['cookTime'] < 0):
		return ErrorCheckReturn(True, 400, 'cookTime of ingredient must be non-negative')

	# check recipe requiredItems have one element per name
	if data['type'] == 'recipe':
		seen_required_items = set()
		for required_item in data['requiredItems']:
			if required_item['name'] in seen_required_items:
				return ErrorCheckReturn(True, 400, 'recipe requiredItems can only have one element per name')
			else:
				seen_required_items.add(required_item['name'])
	
	return ErrorCheckReturn(False, None, None)

# adds ingredient specified by data into the cookbook
def add_ingredient(data: dict) -> None:
	name = data['name']
	cook_time = data['cookTime']
	cookbook.ingredients[name] = Ingredient(name, cook_time)

# adds recipe specified by data into the cookbook
def add_recipe(data: dict) -> None:
	recipe_name = data['name']
	required_items = []
	for item in data['requiredItems']:
		required_item_name = item['name']
		required_item_quantity = item['quantity']
		required_items.append(RequiredItem(required_item_name, required_item_quantity))
	cookbook.recipes[recipe_name] = Recipe(recipe_name, required_items)

# handles the logic for the create_entry POST request
def create_entry_logic(data: dict) -> None:
	if data['type'] == 'ingredient':
		add_ingredient(data)
	elif data['type'] == 'recipe':
		add_recipe(data)


# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route('/entry', methods=['POST'])
def create_entry():
	data = request.get_json()
	error_check_result = create_entry_error_check(data)
	if error_check_result.error_occurred:
		return error_check_result.error_message, error_check_result.error_code
	create_entry_logic(data)

	return jsonify({}), 200


# [TASK 3] ====================================================================
# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route('/summary', methods=['GET'])
def summary():
	# TODO: implement me
	return 'not implemented', 500


# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)
