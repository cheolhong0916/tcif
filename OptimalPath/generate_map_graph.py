#!/usr/bin/env python

import os
import sys
import json
import glob
import random
import argparse
from os.path import join as pjoin
from tqdm import trange
import numpy as np
import networkx as nx
from itertools import permutations
import heapq

import alfworld.agents
from alfworld.info import ALFWORLD_DATA
from alfworld.env.thor_env import ThorEnv
from alfworld.agents.detector.mrcnn import load_pretrained_model
# from alfworld.agents.controller import OracleAgent, OracleAStarAgent, MaskRCNNAgent, MaskRCNNAStarAgent
from alfworld.agents.controller_new import OracleAgent, OracleAStarAgent, MaskRCNNAgent, MaskRCNNAStarAgent
import alfworld.gen.constants as constants
ALFWORLD_DATA = "/home/cheolhong/ch/alfworld"
# Time thresholds for each state change
TIME_THRESHOLDS = {
    'cool': 120,
    'cold': 240,
    'freezing': 360,
    'warm': 40,
    'hot': 80,
    'boiling': 120,
    'rinsed': 20,
    'washed': 40
}
TIME_BOUNDARIES = {
    'cool': [TIME_THRESHOLDS['cool'], TIME_THRESHOLDS['cold']],
    'cold': [TIME_THRESHOLDS['cold'], TIME_THRESHOLDS['freezing']],
    'freezing': [TIME_THRESHOLDS['cool'], int(10e4)],
    'warm': [TIME_THRESHOLDS['warm'], TIME_THRESHOLDS['hot']],
    'hot': [TIME_THRESHOLDS['hot'], TIME_THRESHOLDS['boiling']],
    'boiling': [TIME_THRESHOLDS['boiling'], int(10e4)],
    # 'rinsed': 20,
    'washed': [TIME_THRESHOLDS['washed'], int(10e4)],
}
# constants
RECEPTACLES = set(constants.RECEPTACLES) | {'Sink', 'Bathtub'}
OBJECTS = (set(constants.OBJECTS_WSLICED) - set(RECEPTACLES)) | set(constants.MOVABLE_RECEPTACLES)
OBJECTS -= {'Blinds', 'Boots', 'Cart', 'Chair', 'Curtains', 'Footstool', 'Mirror', 'LightSwtich', 'Painting', 'Poster', 'ShowerGlass', 'Window'}
STATIC_RECEPTACLES = set(RECEPTACLES) - set(constants.MOVABLE_RECEPTACLES)

def setup_scene(env, traj_data, r_idx, args, reward_type='dense'):
    # traj_data: {} -> [{}, {}, ...]
    # scene setup
    scene_num = traj_data[0]['scene']['scene_num']
    object_poses = traj_data[0]['scene']['object_poses']
    dirty_and_empty = traj_data[0]['scene']['dirty_and_empty']
    object_toggles = traj_data[0]['scene']['object_toggles']

    scene_name = 'FloorPlan%d' % scene_num
    env.reset(scene_name)
    env.restore_scene(object_poses, object_toggles, dirty_and_empty)

    # initialize to start position
    env.step(dict(traj_data[0]['scene']['init_action']))

    traj = dict()

    # print goal instr
    print("Task:")
    for td in traj_data:
        print(td['turk_annotations']['anns'][r_idx]['task_desc'])
        traj[td['task_id']] = td
    # setup task for reward
    # env.set_task(traj_data, args, reward_type=reward_type)
    env.set_task(traj, args, reward_type=reward_type)


def generate_graph(layout, recep_objects, spawned_location):
    node_data = {}
    for key, value in recep_objects.items():
        node_data[value["num_id"]] = value

    # Initialize graph
    G = nx.Graph()

    # Add nodes to the graph
    for node_id, info in node_data.items():
        G.add_node(node_id, object_type=info['object_type'], pos=(info['locs']['x'], info['locs']['z']), visible_objects=info['visible_objects'])
    G.add_node('spawned_location', object_type='spawned_location', pos=spawned_location, visible_objects = [])

    # Define movement directions and step size
    directions = [(0.25, 0), (-0.25, 0), (0, 0.25), (0, -0.25)]
    step_size = 1  # Each 0.25 step takes 1 time step

    # Add edges based on Manhattan distance and layout constraints within G
    for node1, data1 in G.nodes(data=True):
        pos1 = data1['pos']
        
        for node2, data2 in G.nodes(data=True):
            if node1 == node2:
                continue
            pos2 = data2['pos']
            
            # Use BFS to find if a path exists within layout constraints
            queue = [(pos1, 0)]  # (position, distance)
            visited = set()
            found_path = False

            while queue:
                current_pos, dist = queue.pop(0)
                if current_pos == pos2:
                    G.add_edge(node1, node2, weight=dist)
                    found_path = True
                    break

                for dx, dz in directions:
                    new_pos = (current_pos[0] + dx, current_pos[1] + dz)
                    if new_pos in layout and new_pos not in visited:
                        queue.append((new_pos, dist + step_size))
                        visited.add(new_pos)
            
            # If no path found, do not add an edge
            if not found_path:
                continue

    # Display the graph
    # print("Graph nodes and edges:")
    # print(G.nodes(data=True),'\n')
    # print(G.edges(data=True))
    return G

global error_log
error_log = ""




########################################################################################################################
# Function to find a specific object in the visible objects of each node and calculate shortest path distance
def get_shortest_path_distance(graph, start_node, target_object):
    
    # if target_object is the node name (e.g., fridge 1)
    if target_object in graph.nodes():
        return target_object, nx.shortest_path_length(graph, start_node, target_object, weight='weight')

    # if target_object is receptacle
    if target_object in STATIC_RECEPTACLES:
        target_nodes = []
        for node, data in graph.nodes(data=True):
            if data['object_type'] == target_object:
                target_nodes.append(node)
        
    else:
        # Iterate through all nodes to find nodes containing the target_object in visible_objects
        target_nodes = []
        for node, data in graph.nodes(data=True):
            visible_objects = data.get('visible_objects', [])
            # Check if the target_object is in any of the visible_objects
            for obj in visible_objects:
                if obj.split('|')[0] == target_object:
                    target_nodes.append(node)
                    break
    
    # If no nodes contain the target object, return None
    if not target_nodes:
        print(f"Object '{target_object}' not found in any visible objects.")
        return None
    
    # Calculate shortest path distance to the nearest node containing the target object
    shortest_distance = float('inf')
    closest_node = None
    for target_node in target_nodes:
        try:
            distance = nx.shortest_path_length(graph, start_node, target_node, weight='weight')
            if distance < shortest_distance:
                shortest_distance = distance
                closest_node = target_node
        except nx.NetworkXNoPath:
            # If there's no path between start_node and target_node, continue
            continue
    
    # Return the closest node and shortest distance
    if closest_node:
        print(f"Closest node containing '{target_object}': {closest_node} with distance {shortest_distance}")
        return closest_node, shortest_distance
    else:
        print(f"No reachable node found for object '{target_object}'")
        return 0,0


def main(args):
    problems = args.problem
    for _ in trange(len(problems)):
        root = problems.pop()
        print(f"Playing '{root}'.")
        for i in os.listdir(root):
            if "trial" in i:
                trial = i
                break
        json_file = os.path.join(root, trial, 'traj_data.json')
        with open(json_file, 'r') as f:
            representative_data = json.load(f)

        with open(os.path.join(root,'receps_objects.json')) as f:
            recep_objects = json.load(f)

        floorplan = representative_data['scene']['floor_plan']
        layout = np.load('alfworld/gen/layouts/' + floorplan + '-layout.npy')
        layout = {tuple(coord) for coord in layout}  # Convert layout to a set of tuples for quick lookup
        spawned_location = (representative_data['scene']['init_action']['x'], representative_data['scene']['init_action']['z'])
        G = generate_graph(layout, recep_objects, spawned_location)
        ##########################################



        ##########################################


if __name__ == "__main__":
    description = "Play the abstract text version of an ALFRED environment."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("problem", nargs="?", default=None,
                        help="Path to a folder containing PDDL and traj_data files."
                             f"Default: pick one at random found in {ALFWORLD_DATA}")
    parser.add_argument("--controller", default="oracle", choices=["oracle", "oracle_astar", "mrcnn", "mrcnn_astar"])
    parser.add_argument("--debug", action="store_true")
    parser.add_argument('--load_receps', action="store_true")
    parser.add_argument('--reward_config', type=str, default=pjoin(alfworld.agents.__path__[0], 'config', 'rewards.json'))
    parser.add_argument('--split', type=str)
    args = parser.parse_args()

    if args.problem is None:

        ### json_3.0.3
        json_path = os.path.join(ALFWORLD_DATA, "json_3.0.6/"+args.split)
        problems = [os.path.join(json_path, item) for item in os.listdir(json_path)]
        args.problem = problems

    if "movable_recep" in args.problem:
        raise ValueError("This problem contains movable receptacles, which is not supported by ALFWorld.")

    main(args)

