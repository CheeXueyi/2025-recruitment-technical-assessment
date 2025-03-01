from dataclasses import dataclass
from typing import List, Dict, Union, TypedDict
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
	# recipe name -> Recipe object
	recipes: Dict[str, Recipe]
	# ingredient name -> Ingredient object
	ingredients: Dict[str, Ingredient]

	def __init__(self):
		self.recipes = {}
		self.ingredients = {}

class SummaryReturn(TypedDict):
	name: str
	cookTime: int
	ingredients: List[RequiredItem]


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
def create_entry_error_check(data: Dict) -> ErrorCheckReturn:
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
def add_recipe(data: Dict) -> None:
	recipe_name = data['name']
	required_items = []
	for item in data['requiredItems']:
		required_item_name = item['name']
		required_item_quantity = item['quantity']
		required_items.append(RequiredItem(required_item_name, required_item_quantity))
	cookbook.recipes[recipe_name] = Recipe(recipe_name, required_items)

# handles the logic for the create_entry POST request
def create_entry_logic(data: Dict) -> None:
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
# recursive helper function to check if a recipe is valid
def recipe_is_valid_recurse(item_name: str, is_valid: Dict[str, bool]) -> bool:
	# check if we have previously checked this item
	if item_name in is_valid:
		return is_valid[item_name]
	
	if item_name in cookbook.ingredients:
		# item is an ingredient
		is_valid[item_name] = True
		return True
	elif item_name in cookbook.recipes:
		# item is a recipe
		recipe = cookbook.recipes[item_name]
		# check validity of each required item
		for required_item in recipe.required_items:
			if not recipe_is_valid_recurse(required_item.name, is_valid):
				# some required item is not valid
				is_valid[item_name] = False
				return False
		# every required item is valid, so this item is valid
		is_valid[item_name] = True
		return True
	else:
		# item is not registered in cookbook
		is_valid[item_name] = False
		return False

# for a given recipe name, returns true all of its required ingredients and recipes are
# registered in the cookbook
def recipe_is_valid(recipe_name: str) -> bool:
	# memoisation to increase performance 
	is_valid = {}
	return recipe_is_valid_recurse(recipe_name, is_valid)

# checks for errors for the given recipe name for the summary GET request
def summary_error_check(recipe_name: str) -> ErrorCheckReturn:
	# check if queried recipe is an ingredient
	if recipe_name in cookbook.ingredients:
		return ErrorCheckReturn(True, 400, 'Searched name is an ingredient')
	
	# check if queried recipe is in the recipes list
	if recipe_name not in cookbook.recipes:
		return ErrorCheckReturn(True, 400, f'Cannot find recipe of name {recipe_name}')
	
	# check if there are any required items that are not in cookbook
	if not recipe_is_valid(recipe_name):
		return ErrorCheckReturn(True, 400, 'Recipe depends on some item that is not in the cook book')

	return ErrorCheckReturn(False, None, None)

# recursively updates the ingredients_quantity map with the ingredients needed by recipe with recipe_name
def update_ingredients(item_name: str, ingredients_quantity: Dict[str, int], quantity_needed: int) -> None:
	if item_name in cookbook.ingredients:
		# item is an ingredient
		if item_name in ingredients_quantity:
			ingredients_quantity[item_name] += quantity_needed
		else:
			ingredients_quantity[item_name] = quantity_needed
	else:
		# item is a recipe
		recipe = cookbook.recipes[item_name]
		for required_item in recipe.required_items:
			# update ingredients for each required ingredient of current recipe
			update_ingredients(required_item.name, ingredients_quantity, quantity_needed * required_item.quantity)

# handles the logic of the summary GET request
def summary_logic(recipe_name: str) -> SummaryReturn:
	# stores all the ingredient_name -> quantity needed for current recipe
	ingredients_quantity: Dict[str, int] = {}
	update_ingredients(recipe_name, ingredients_quantity, 1)

	# format ingredients for output
	ingredients = []
	# calculate total cook time based on ingredients
	total_cook_time = 0
	for name, quantity in ingredients_quantity.items():
		ingredients.append(RequiredItem(name, quantity))
		total_cook_time += cookbook.ingredients[name].cook_time * quantity
	
	return {'name': recipe_name, 'cookTime': total_cook_time, 'ingredients': ingredients}


# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route('/summary', methods=['GET'])
def summary():
	recipe_name = request.args.get('name')
	error_check_result = summary_error_check(recipe_name)
	if error_check_result.error_occurred:
		return error_check_result.error_message, error_check_result.error_code
	result = summary_logic(recipe_name)
	return jsonify(result), 200


# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)
