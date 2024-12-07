export PYTHONPATH="$(pwd)/.."
export DISPLAY=":1"

python save_locations.py "$@"
# python save_locations.py --controller oracle_astar