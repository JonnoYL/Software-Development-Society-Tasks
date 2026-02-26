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
def parse_handwriting(recipeName: str) -> Union[str, None]:
    if not isinstance(recipeName, str):
        return None

    # Replace hyphens/underscores with spaces
    s = recipeName.replace('-', ' ').replace('_', ' ')

    # Remove all non-letters and non-whitespace
    s = re.sub(r'[^A-Za-z\s]', '', s)

    # Collapse whitespace and trim
    s = re.sub(r'\s+', ' ', s).strip()

    # Must be non-empty
    if len(s) == 0:
        return None

    # Title case each word (first letter uppercase, rest lowercase)
    words = s.split(' ')
    s = ' '.join(w[0].upper() + w[1:].lower() for w in words)

    return s


# [TASK 2] ====================================================================
@app.route('/entry', methods=['POST'])
def create_entry():
	# Read JSON body and check if it's not valid JSON or not an object
	data = request.get_json(silent=True)
	if not isinstance(data, dict):
		return ('', 400)

	# Extract basic fields used by both recipes and ingredients
	entry_type = data.get('type')
	raw_name = data.get('name')

	# Validate entry type
	if entry_type not in ('recipe', 'ingredient'):
		return ('', 400)

	# Validate name is a string
	if not isinstance(raw_name, str):
		return ('', 400)

	# parse_handwriting the name
	parsed_name = parse_handwriting(raw_name)
	if parsed_name is None:
		return ('', 400)

	# Ensure uniqueness of entry names
	if parsed_name in cookbook:
		return ('', 400)

	# Ingredient
	if entry_type == 'ingredient':
		# Ingredients cookTime must be an int >= 0
		cook_time = data.get('cookTime')
		if not isinstance(cook_time, int) or cook_time < 0:
			return ('', 400)

		# Store the Ingredient object in cookbook
		cookbook[parsed_name] = Ingredient(name=parsed_name, cook_time=cook_time)
		return ('', 200)

	# Recipe
	required_items_raw = data.get('requiredItems')

	# Recipes require requiredItems
	if not isinstance(required_items_raw, list):
		return ('', 400)

	required_items: List[RequiredItem] = []

	# Ensure no duplicate requiredItem names
	seen_names = set()

	# Validate each required item entry in the list
	for item in required_items_raw:
		if not isinstance(item, dict):
			return ('', 400)

		item_name = item.get('name')
		item_qty = item.get('quantity')

		# Name must be a string
		if not isinstance(item_name, str):
			return ('', 400)

		# Quantity must be an int > 0
		if not isinstance(item_qty, int) or item_qty <= 0:
			return ('', 400)

		# Normalise required item name
		parsed_item_name = parse_handwriting(item_name)
		if parsed_item_name is None:
			return ('', 400)

		# requiredItems can only have one element per name
		if parsed_item_name in seen_names:
			return ('', 400)
		seen_names.add(parsed_item_name)

		# Convert into a RequiredItem to store
		required_items.append(RequiredItem(name=parsed_item_name, quantity=item_qty))

	# Store the Recipe
	cookbook[parsed_name] = Recipe(name=parsed_name, required_items=required_items)
	return ('', 200)


# [TASK 3] ====================================================================
@app.route('/summary', methods=['GET'])
def summary():
	# Read the recipe name
	raw_name = request.args.get('name', '')

	# parse_handwriting the name
	parsed_name = parse_handwriting(raw_name)
	if parsed_name is None:
		return ('', 400)

	# Requested entry must exist and be a Recipe
	entry = cookbook.get(parsed_name)
	if entry is None or not isinstance(entry, Recipe):
		return ('', 400)

	# Compute summary
	try:
		total_cook_time, aggregated = _summarise_recipe(parsed_name)
	except ValueError:
		return ('', 400)

	# Convert dict into the required list-of-objects format
	ingredients_list = [{"name": n, "quantity": q} for n, q in aggregated.items()]

	return jsonify({
		"name": parsed_name,
		"cookTime": total_cook_time,
		"ingredients": ingredients_list
	}), 200


def _summarise_recipe(recipe_name: str) -> Tuple[int, Dict[str, int]]:
    # Track the recursion stack to detect cycles (e.g. A depends on B depends on A)
    visited = set()

    def dfs(name: str, multiplier: int) -> Tuple[int, Dict[str, int]]:
        # Check entry by name
        entry = cookbook.get(name)
        if entry is None:
            raise ValueError("Missing entry")

        # Base case: ingredient -> cook time contributes cook_time * multiplier + contributes 'multiplier' units
        if isinstance(entry, Ingredient):
            return entry.cook_time * multiplier, {entry.name: multiplier}

        # If not an Ingredient, must be Recipe
        if not isinstance(entry, Recipe):
            raise ValueError("Unknown entry type")

        # If same recipe seen again in the current path -> cycle detected
        if name in visited:
            raise ValueError("Cycle detected")
        visited.add(name)

        total_time = 0
        agg: Dict[str, int] = {}

        # Recurse into each item in recipe
		# -> multiple by current multiplier
		# -> aggregate total cooktime + ingredient quantities
        for req in entry.required_items:
            req_name = req.name
            qty = req.quantity

            # Recurse with updated multiplier
            t, sub = dfs(req_name, multiplier * qty)
            total_time += t

            # Merge returned ingredient quantities recipe
            for ing_name, ing_qty in sub.items():
                agg[ing_name] = agg.get(ing_name, 0) + ing_qty

        # Remove from recursion stack
        visited.remove(name)
        return total_time, agg

    # Start DFS from target recipe with multiplier 1
    return dfs(recipe_name, 1)

# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)
