# Set environment variables
export PYTHONPATH="$(pwd)/.."
export DISPLAY=":1"

# Change directory to the location where the script expects to find files
cd "$(dirname "$0")/.." || exit 1

# Execute the Python script
python OptimalPath/get_optimal_path.py "$@"

# #!/bin/bash

# # Define the necessary variables
# PYTHONPATH=$(pwd)/..
# DISPLAY=:1
# PYTHON_EXEC="/home/cheolhong/anaconda3/envs/alfworld/bin/python"
# SCRIPT="OptimalPath/get_optimal_path.py"

# # Execute the Python script with the specified arguments and environment variables
# $PYTHON_EXEC $SCRIPT \
#     --controller oracle_astar \
#     --split train \
#     --start_idx 0 \
#     --end_idx 50