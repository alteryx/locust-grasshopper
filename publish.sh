rm -rf dist
bumpversion patch
python3 -m build
python3 -m twine upload dist/* --verbose
