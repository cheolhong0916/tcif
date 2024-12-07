import os
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import json
import alfworld.agents
from alfworld.info import ALFWORLD_DATA
from alfworld.env.thor_env import ThorEnv
from alfworld.agents.detector.mrcnn import load_pretrained_model
# from alfworld.agents.controller import OracleAgent, OracleAStarAgent, MaskRCNNAgent, MaskRCNNAStarAgent
from alfworld.agents.controller_new import OracleAgent, OracleAStarAgent, MaskRCNNAgent, MaskRCNNAStarAgent

ALFWORLD_DATA = os.getcwd()

# Load layout and trial data
num = "10"
layout = np.load('alfworld/gen/layouts/FloorPlan'+num+'-layout.npy')

trial = '2_pick_cool_then_place_in_recep-Bread-None-CounterTop-10__pick_heat_then_place_in_recep-Mug-None-Cabinet-10/trial_T20190908_091747_866951'

with open('json_3.0.6/valid_unseen/'+trial+'/traj_data.json') as f:
    traj_data = json.load(f)
with open('json_3.0.6/valid_unseen/'+trial+'/receps.json') as f:
    receps = json.load(f)

# Extract agent_spawned_position
agent_spawned_position = [
    traj_data['scene']['init_action']['x'],
    traj_data['scene']['init_action']['z']
]
# agent_spawned_position = [round(coord * 4) / 4 for coord in agent_spawned_position]  # Round to nearest 0.25

# Get coordinates of receptacles
receps_coordinates = {}
for i in list(receps.keys()):
    receps_coordinates[receps[i]['num_id']] = [receps[i]['locs']['x'], receps[i]['locs']['z']]

# Get coordinates of objects
def get_objects_coordinates(traj_data):
    objects_coordinates = {}
    num = 1
    object_target = traj_data['pddl_params']['object_target']
    for i in traj_data['scene']['object_poses']:
        if i['objectName'].split('_')[0] == object_target:
            x = i['position']['x']; z = i['position']['z']
            x = round(x * 4) / 4; z = round(z * 4) / 4
            objects_coordinates[object_target.lower() + ' ' + str(num)] = [x, z]
            num += 1
    return objects_coordinates



objects_coordinates = get_objects_coordinates(traj_data)











# Create graph and add nodes for receptacles, objects, and agent
G = nx.Graph()
node_positions = {}
for node, coord in {**receps_coordinates, **objects_coordinates}.items():
    G.add_node(node)
    node_positions[node] = coord

# Add the agent's spawned position as a node
G.add_node("agent_start")
node_positions["agent_start"] = agent_spawned_position

# Add edges based on Manhattan distance between nodes
for node1, pos1 in node_positions.items():
    for node2, pos2 in node_positions.items():
        if node1 != node2:
            manhattan_distance = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
            G.add_edge(node1, node2, weight=manhattan_distance)

# Plot layout as background
plt.figure(figsize=(8, 8))
plt.scatter(layout[:, 0], layout[:, 1], c='lightgrey', s=100, label="Layout points")

# Draw graph nodes and edges on top of the layout
nx.draw_networkx_edges(G, pos=node_positions, edge_color='red', alpha=0.5)
nx.draw_networkx_nodes(G, pos=node_positions, node_size=300, node_color='blue', label="Nodes")
nx.draw_networkx_labels(G, pos=node_positions, font_size=8)

# Highlight agent's start position
plt.scatter(
    agent_spawned_position[0], agent_spawned_position[1],
    color='green', s=200, marker='*', label="Agent Start Position"
)

# Set axis labels and title
plt.xlabel('X coordinate')
plt.ylabel('Z coordinate')
plt.title("Graph Visualization on Layout with Agent Start Position")

# Add numeric labels to both x and y axes with a 1-unit interval
plt.xticks(np.arange(int(min(layout[:, 0])), int(max(layout[:, 0])) + 1, 1))  # 1-unit step size
plt.yticks(np.arange(int(min(layout[:, 1])), int(max(layout[:, 1])) + 1, 1))  # 1-unit step size

# Adjust the legend position to be right below the title
plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=True, fontsize='small')

plt.grid(True)

# Save the plot as an image file
plt.savefig('vis/Graph_FloorPlan'+num+'.png')  # Save as PNG file

