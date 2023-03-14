rm -rf dist
bumpversion patch
python3 -m build
python3 -m twine upload --config-file .pypirc -r local dist/* --verbose
