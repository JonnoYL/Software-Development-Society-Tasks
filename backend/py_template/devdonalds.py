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


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook = None

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
	# TODO: implement me
	return 'not implemented', 500


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
