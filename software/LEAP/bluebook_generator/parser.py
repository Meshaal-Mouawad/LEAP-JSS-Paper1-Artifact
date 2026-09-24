from pathlib import Path  # Add this line at the top


def extract_formula_from_comments(code_lines):
    """
    Look for lines containing 'Formula:' and return the formula string.
    """
    for line in code_lines:
        if "Formula:" in line:
            # Extract everything after 'Formula:'
            return line.split("Formula:", 1)[1].strip()
    return None


# In bluebook_generator/parser.py, fix the loop:
def find_kpis_in_directory(directory):
    # ...existing code...
    files = list(Path(directory).glob("**/*.py"))  # Define files first!
    for filepath in files:  # Now use filepath consistently
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # ...existing code...
        # Try to extract formula from comments
        extract_formula_from_comments(lines)
        # ...existing code...
    # ...existing code...
