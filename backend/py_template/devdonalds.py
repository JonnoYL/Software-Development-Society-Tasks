from dataclasses import dataclass
from typing import List, Dict, Union, Tuple
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


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook: Dict[str, Union[Recipe, Ingredient]] = {}

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
# Takes in a recipeName and returns it in a form that
def parse_handwriting(recipeName: str) -> Union[str, None]:
    if not isinstance(recipeName, str):
        return None

    original = recipeName

    # Replace all hyphens and underscores with whitespace
    s = original.replace('-', ' ').replace('_', ' ')

    # Keep only letters and whitespaces (and remove everything else)
    s = re.sub(r'[^A-Za-z\s]', '', s)

    # Squash multiple whitespaces, trim leading/trailing
    s = re.sub(r'\s+', ' ', s).strip()

    # If empty, return None
    if len(s) == 0:
        return None

    # Capitalise first letter of each word, rest lowercase
    words = s.split(' ')
    s = ' '.join(w[:1].upper() + w[1:].lower() for w in words if w)

    # If input already satisfies all conditions, return the original input
    if s == original:
        return original

    return s


# [TASK 2] ====================================================================
# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route('/entry', methods=['POST'])
def create_entry():
	data = request.get_json(silent=True)
	if not isinstance(data, dict):
		return ('', 400)

	entry_type = data.get('type')
	raw_name = data.get('name')

	if entry_type not in ('recipe', 'ingredient'):
		return ('', 400)
	if not isinstance(raw_name, str):
		return ('', 400)

	parsed_name = parse_handwriting(raw_name)
	if parsed_name is None:
		return ('', 400)

	# Names must be unique
	if parsed_name in cookbook:
		return ('', 400)

	if entry_type == 'ingredient':
		cook_time = data.get('cookTime')
		if not isinstance(cook_time, int) or cook_time < 0:
			return ('', 400)

		cookbook[parsed_name] = Ingredient(name=parsed_name, cook_time=cook_time)
		return ('', 200)

	# entry_type == 'recipe'
	required_items_raw = data.get('requiredItems')
	if not isinstance(required_items_raw, list):
		return ('', 400)

	required_items: List[RequiredItem] = []
	seen_names = set()

	for item in required_items_raw:
		if not isinstance(item, dict):
			return ('', 400)

		item_name = item.get('name')
		item_qty = item.get('quantity')

		if not isinstance(item_name, str):
			return ('', 400)
		if not isinstance(item_qty, int) or item_qty <= 0:
			return ('', 400)

		parsed_item_name = parse_handwriting(item_name)
		if parsed_item_name is None:
			return ('', 400)

		# requiredItems can only have one element per name
		if parsed_item_name in seen_names:
			return ('', 400)
		seen_names.add(parsed_item_name)

		required_items.append(RequiredItem(name=parsed_item_name, quantity=item_qty))

	cookbook[parsed_name] = Recipe(name=parsed_name, required_items=required_items)
	return ('', 200)


# [TASK 3] ====================================================================
# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route('/summary', methods=['GET'])
def summary():
	# Read + parse query name
	raw_name = request.args.get('name', '')
	parsed_name = parse_handwriting(raw_name)
	if parsed_name is None:
		return ('', 400)

	# Must exist and must be a recipe (not an ingredient)
	entry = cookbook.get(parsed_name)
	if entry is None or not isinstance(entry, Recipe):
		return ('', 400)

	try:
		total_cook_time, aggregated = _summarise_recipe(parsed_name)
	except ValueError:
		# Any invalid structure / missing dependency => 400
		return ('', 400)

	ingredients_list = [{"name": n, "quantity": q} for n, q in aggregated.items()]
	return jsonify({
		"name": parsed_name,
		"cookTime": total_cook_time,
		"ingredients": ingredients_list
	}), 200


def _summarise_recipe(recipe_name: str) -> Tuple[int, Dict[str, int]]:
	"""
	Returns:
	- total cook time (int)
	- aggregated base ingredients {ingredient_name: total_quantity}

	Raises Error if:
	- recipe/ingredient referenced doesn't exist in cookbook
	- a requiredItem name resolves to an invalid name
	- cycle detected (recipe depends on itself indirectly)
	"""
	visited = set() # cycle detection for recipes

	def dfs(name: str, multiplier: int) -> Tuple[int, Dict[str, int]]:
		entry = cookbook.get(name)
		if entry is None:
			raise ValueError("Missing entry")

		# Base ingredient
		if isinstance(entry, Ingredient):
			if entry.cook_time < 0:
				raise ValueError("Invalid cook_time")
			return entry.cook_time * multiplier, {entry.name: multiplier}

		# Recipe
		if not isinstance(entry, Recipe):
			raise ValueError("Unknown entry type")

		if name in visited:
			raise ValueError("Cycle detected")
		visited.add(name)

		total_time = 0
		agg: Dict[str, int] = {}

		# Behaviour for empty required_items undefined
		for req in entry.required_items:
			parsed_req_name = parse_handwriting(req.name)
			if parsed_req_name is None:
				raise ValueError("Invalid required item name")

			qty = req.quantity
			if not isinstance(qty, int) or qty <= 0:
				raise ValueError("Invalid quantity")

			t, sub = dfs(parsed_req_name, multiplier * qty)
			total_time += t
			for ing_name, ing_qty in sub.items():
				agg[ing_name] = agg.get(ing_name, 0) + ing_qty

		visited.remove(name)
		return total_time, agg

	return dfs(recipe_name, 1)

# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)
