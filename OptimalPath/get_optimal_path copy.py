#!/usr/bin/env python
import re
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
    # Sample recep_objects for demonstration
    # recep_objects = {
    #     "DiningTable|-02.20|+00.99|+00.45": {
    #         "object_id": "DiningTable|-02.20|+00.99|+00.45",
    #         "object_type": "DiningTable",
    #         "locs": {
    #             "action": "TeleportFull",
    #             "x": -2.25,
    #             "y": 0.9009992,
    #             "z": -0.25,
    #             "rotateOnTeleport": False,
    #             "rotation": 0,
    #             "horizon": 30
    #         },
    #         "num_pixels": 24534,
    #         "num_id": "diningtable 1",
    #         "closed": None,
    #         "visible_objects": [
    #             "Bread|-02.07|+01.04|+00.17",
    #             "Cup|-02.34|+00.95|+00.26",
    #             "Lettuce|-02.07|+01.04|+00.61",
    #             "Bowl|-01.79|+00.95|+00.52",
    #             "Lettuce|-01.79|+01.04|+00.26",
    #             "DishSponge|-02.20|+00.95|+00.44",
    #             "DishSponge|-02.61|+00.95|+00.61",
    #             "SaltShaker|-02.61|+00.95|+00.44",
    #             "Fork|-02.61|+00.95|+00.26",
    #             "Potato|-01.79|+00.98|+00.70",
    #             "Fork|-01.93|+00.95|+00.44"
    #         ]
    #     }
    # }

    # Convert recep_objects to have "num_id" as key
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
def get_shortest_path_distance(graph, start_node, object_target):
    
    # if object_target is the node name (e.g., fridge 1)
    if object_target in graph.nodes():
        return object_target, nx.shortest_path_length(graph, start_node, object_target, weight='weight')

    # if object_target is receptacle
    if object_target in STATIC_RECEPTACLES:
        target_nodes = []
        for node, data in graph.nodes(data=True):
            if data['object_type'] == object_target:
                target_nodes.append(node)
        
    else:
        # Iterate through all nodes to find nodes containing the object_target in visible_objects
        target_nodes = []
        for node, data in graph.nodes(data=True):
            visible_objects = data.get('visible_objects', [])
            # Check if the object_target is in any of the visible_objects
            for obj in visible_objects:
                if obj.split('|')[0] == object_target:
                    target_nodes.append(node)
                    break
    
    # If no nodes contain the target object, return None
    if not target_nodes:
        print(f"Object '{object_target}' not found in any visible objects.")
        return 0,0
    
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
        print(f"Closest node containing '{object_target}': {closest_node} with distance {shortest_distance}")
        return closest_node, shortest_distance
    else:
        print(f"No reachable node found for object '{object_target}'")
        return 0,0



def find_instances(input_text, target_obj):
    pattern = rf"\b{target_obj.lower()} \d+\b"
    instances = re.findall(pattern, input_text.lower())
    return instances

# Using a Microwave
def start_heating(G, current_node, subtask, env, agent):
    actions = []; total_time = 0
    target_obj = subtask['object_target']
    next_node, time_taken = get_shortest_path_distance(G, current_node, target_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0, 0
    actions.append("go to " + next_node)
    agent.step("go to " + next_node)
    current_node = next_node
    print(agent.feedback)
    if "Nothing happens" == agent.feedback:
        return 0,0,0,0

    instances = find_instances(agent.feedback, target_obj)
    target_obj_instance = instances[0]
    actions.append("take "+target_obj_instance+" from "+current_node)
    agent.step("take "+target_obj_instance+" from "+current_node)
    total_time += 1


    for visible_object in G.nodes[current_node]['visible_objects']:
        if visible_object.split('|')[0] == target_obj:
            G.nodes[current_node]['visible_objects'].remove(visible_object)
            break

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'microwave 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0, 0
    actions.append("go to microwave 1")

    total_time += 1
    actions.append("open microwave 1")

    total_time += 1
    actions.append("put " + target_obj + " in microwave 1")

    total_time += 1
    actions.append("close microwave 1")

    total_time += 1
    actions.append("toggleon microwave 1")

    return actions, total_time, 'microwave 1', env, target_obj_instance

def finish_heating(G, current_node, subtask):
    actions = []; total_time = 0
    target_obj = subtask['object_target']
    parent_obj = subtask['parent_target']

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'microwave 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("toggleoff microwave 1")
    total_time += 1

    actions.append("open microwave 1")
    total_time += 1

    actions.append("take " + target_obj + " from microwave 1")
    total_time += 1
    for visible_object in G.nodes[current_node]['visible_objects']:
        if visible_object.split('|')[0] == target_obj:
            G.nodes[current_node]['visible_objects'].remove(visible_object)
            break

    actions.append("close microwave 1")
    total_time += 1

    actions.append("toggleoff microwave 1")
    total_time += 1

    next_node, time_taken = get_shortest_path_distance(G, current_node, parent_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("put " + target_obj + " on/in " + parent_obj)
    total_time += 1

    return actions, total_time, current_node

# Using a Stoveburner
def start_heating_using_stoveburner(G, current_node, task):
    actions = []; total_time = 0
    target_obj = task[1]
    next_node, time_taken = get_shortest_path_distance(G, current_node, target_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("take "+target_obj+" from "+current_node)

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'pot 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to pot 1")
    current_node = next_node

    total_time += 1
    actions.append("put " + target_obj + " in pot 1")

    total_time += 1
    actions.append("take pot 1 from " + current_node)

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'sinkbasin 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to sinkbasin 1")
    current_node = next_node

    total_time += 1
    actions.append("put pot 1 on sinkbasin 1")

    total_time += 1
    actions.append("toggleon faucet 1")

    total_time += 1
    actions.append("toggleoff faucet 1")

    total_time += 1
    actions.append("take pot 1 from sinkbasin 1")

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'stoveburner 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to stoveburner 1")
    current_node = next_node

    total_time += 1
    actions.append("put pot 1 on stoveburner 1")

    total_time += 1
    actions.append("toggleon stoveburner 1")

    return actions, total_time, 'stoveburner 1'


def start_cooling(G, current_node, subtask, env, agent):
    actions = []; total_time = 0
    target_obj = subtask['object_target']

    next_node, time_taken = get_shortest_path_distance(G, current_node, target_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0,0,0,0

    actions.append("go to " + next_node)
    agent.step("go to " + next_node)
    current_node = next_node
    print(agent.feedback)
    if "Nothing happens" in agent.feedback:
        return 0,0,0,0

    
    actions.append("take "+target_obj+" from "+current_node)
    agent.step("take "+target_obj+" from "+current_node)
    print(agent.feedback)
    if "Nothing happens" in agent.feedback:
        return 0,0,0,0
    total_time += 1

    for visible_object in G.nodes[current_node]['visible_objects']:
        if visible_object.split('|')[0] == target_obj:
            G.nodes[current_node]['visible_objects'].remove(visible_object)
            break

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'fridge 1')
    if next_node: total_time += time_taken
    else: return 0, 0, 0, 0
    actions.append("go to fridge 1")
    agent.step("go to fridge 1")
    print(agent.feedback)
    if "Nothing happens" in agent.feedback:
        return 0,0,0,0  


    total_time += 1
    actions.append("open fridge 1")
    agent.step("open fridge 1")

    total_time += 1
    actions.append("put " + target_obj + " in fridge 1")
    agent.step(("put " + target_obj + " in fridge 1"))


    total_time += 1
    actions.append("close fridge 1")

    return actions, total_time, 'fridge 1'


def finish_cooling(G, current_node, subtask):
    actions = []; total_time = 0
    target_obj = subtask['object_target']
    parent_obj = subtask['parent_target']

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'fridge 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("open fridge 1")
    total_time += 1

    actions.append("take " + target_obj + " from fridge 1")
    total_time += 1
    for visible_object in G.nodes[current_node]['visible_objects']:
        if visible_object.split('|')[0] == target_obj:
            G.nodes[current_node]['visible_objects'].remove(visible_object)

    actions.append("close fridge 1")
    total_time += 1

    next_node, time_taken = get_shortest_path_distance(G, current_node, parent_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0, 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("put " + target_obj + " in fridge 1")
    total_time += 1

    return actions, total_time, current_node



def start_cleaning(G, current_node, subtask):
    actions = []; total_time = 0
    target_obj = subtask['object_target']
    next_node, time_taken = get_shortest_path_distance(G, current_node, target_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("take "+target_obj+" from "+current_node)
    total_time += 1
    for visible_object in G.nodes[current_node]['visible_objects']:
        if visible_object.split('|')[0] == target_obj:
            G.nodes[current_node]['visible_objects'].remove(visible_object)

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'sinkbasin 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0
    actions.append("go to sinkbasin 1")

    total_time += 1
    actions.append("put "+target_obj+" on sinkbasin 1")

    total_time += 1
    actions.append("toggleon faucet 1")

    return actions, total_time, 'sinkbasin 1'


def finish_cleaning(G, current_node, subtask):
    actions = []; total_time = 0
    target_obj = subtask['object_target']
    parent_obj = subtask['parent_target']

    next_node, time_taken = get_shortest_path_distance(G, current_node, 'sinkbasin 1')
    if next_node:
        total_time += time_taken
    else:
        return 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("toggleoff faucet 1")
    total_time += 1

    actions.append("take "+target_obj+" from "+current_node)
    total_time += 1
    for visible_object in G.nodes[current_node]['visible_objects']:
        if visible_object.split('|')[0] == target_obj:
            G.nodes[current_node]['visible_objects'].remove(visible_object)

    next_node, time_taken = get_shortest_path_distance(G, current_node, parent_obj)
    if next_node:
        total_time += time_taken
    else:
        return 0, 0
    actions.append("go to " + next_node)
    current_node = next_node

    actions.append("put "+ target_obj + " on/in " + parent_obj)
    total_time += 1

    return actions, total_time, subtask['parent_target']

# def execute_subtask(G, current_node, current_task, start=True):
#     if start:
#         if current_task[1] == "pick_heat_then_place_in_recep":      actions, time_taken, updated_node = start_heating(G, current_node, current_task)
#         elif current_task[1] == "pick_cool_then_place_in_recep":    actions, time_taken, updated_node = start_cooling(G, current_node, current_task)
#         elif current_task[1] == "pick_clean_then_place_in_recep":   actions, time_taken, updated_node = start_cleaning(G, current_node, current_task)
#     else:
#         if current_task[1] == "pick_heat_then_place_in_recep":      actions, time_taken, updated_node = finish_heating(G, updated_node, current_task)
#         elif current_task[1] == "pick_cool_then_place_in_recep":    actions, time_taken, updated_node = finish_cooling(G, updated_node, current_task)
#         elif current_task[1] == "pick_clean_then_place_in_recep":   actions, time_taken, updated_node = finish_cleaning(G, updated_node, current_task)        
#     return actions, time_taken, updated_node

def execute_subtask(G, current_node, subtask, env, agent):
    if subtask['stage'] == 'start':
        if subtask['task_type'] == "pick_heat_then_place_in_recep":      actions, time_taken, updated_node, env = start_heating(G, current_node, subtask, env, agent)
        elif subtask['task_type'] == "pick_cool_then_place_in_recep":    actions, time_taken, updated_node, env = start_cooling(G, current_node, subtask, env, agent)
        elif subtask['task_type'] == "pick_clean_then_place_in_recep":   actions, time_taken, updated_node, env = start_cleaning(G, current_node, subtask, env, agent)
    else:
        if subtask['task_type'] == "pick_heat_then_place_in_recep":      actions, time_taken, updated_node, env = finish_heating(G, current_node, subtask, env, agent)
        elif subtask['task_type'] == "pick_cool_then_place_in_recep":    actions, time_taken, updated_node, env = finish_cooling(G, current_node, subtask, env, agent)
        elif subtask['task_type'] == "pick_clean_then_place_in_recep":   actions, time_taken, updated_node, env = finish_cleaning(G, current_node, subtask, env, agent)
    return actions, time_taken, updated_node, env
# first try
def check_feasibility(G, last_node, tasks, task_num, available_time_boundary, total_actions, total_time, started_tasks):
    finished = []
    previous_task = 0
    if task_num > 0:
        previous_task = tasks[task_num-1]
    if task_num >= len(tasks):
        return total_actions, total_time
    
    current_task = tasks[task_num]
    
    # go to the current task's milestone
    actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
    # get time to go back to finish previous task
    _, time_taken_to_go_back = get_shortest_path_distance(G, updated_node, last_node)

    left_time = available_time_boundary[1]
    if time_taken + time_taken_to_go_back > left_time:
        if previous_task:
            if available_time_boundary[0] > 0:
                # wait for the state change
                total_actions.append("wait for " + str(available_time_boundary[0]) + " time steps")
                total_time += available_time_boundary[0]

            # finish the previous task
            actions, time_taken, updated_node = execute_subtask(G, last_node, previous_task, start=False)
            total_actions.extend(actions)
            total_time += time_taken

        # start the current task
        actions, time_taken, updated_node = execute_subtask(G, updated_node, current_task, start=True)
        total_actions.extend(actions)
        total_time += time_taken
        heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]], current_task))

        # check the next task's feasibility
        total_actions, total_time = check_feasibility(G, updated_node, tasks, task_num + 1, TIME_BOUNDARIES[current_task[3]], total_actions, total_time, started_tasks)

        
    else:
        # go to the current task's milestone
        actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
        total_actions.extend(actions)
        total_time += time_taken
        heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]], current_task))

            
def update_priority_queue(queue, subtract_value):
    temp_queue = []
    
    for first, second, task in queue:
        updated_first = first - subtract_value
        updated_second = second - subtract_value
        temp_queue.append((updated_first, updated_second, task))
    
    heapq.heapify(temp_queue)
    return temp_queue

# gpt
def check_feasibility(G, last_node, tasks, task_num, total_actions, total_time, started_tasks):
    # If there are no tasks left to process, return accumulated actions and time
    if task_num >= len(tasks) and not started_tasks:
        return total_actions, total_time
    
    # Identify the current task and the prior task if available
    current_task = tasks[task_num] if task_num < len(tasks) else None

    # Go to the current task's milestone if it exists
    if current_task:
        if len(started_tasks) > 0 :

            actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
            _, time_taken_to_go_back = get_shortest_path_distance(G, updated_node, last_node)

            # Check if starting the next task would exceed the time boundary
            if time_taken + time_taken_to_go_back > started_tasks[0][0]:

                # Complete the task as the time boundary allows
                if started_tasks[0][1] > 0:
                    total_actions.append(f"wait for {started_tasks[0][1]} time steps")
                    total_time += started_tasks[0][1]
                    started_tasks = update_priority_queue(started_tasks, started_tasks[0][1])
                actions, time_taken, updated_node = execute_subtask(G, last_node, started_tasks[0][2], start=False)
                total_actions.extend(actions)
                total_time += time_taken
                started_tasks = update_priority_queue(started_tasks, time_taken)
                _, _, _ = heapq.heappop(started_tasks)

                total_actions_, total_time_ = check_feasibility(G, updated_node, tasks, task_num, total_actions, total_time, started_tasks)
                if total_actions_:
                    total_actions = total_actions_; total_time = total_time_


            else:
                # We can start the new task and add it to the queue of started tasks
                actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
                total_actions.extend(actions)
                total_time += time_taken
                started_tasks = update_priority_queue(started_tasks, time_taken)
                heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]][1], TIME_BOUNDARIES[current_task[3]][0], current_task))

                # If there are further tasks, proceed recursively
                if task_num + 1 < len(tasks):
                    total_actions, total_time = check_feasibility(
                        G, updated_node, tasks, task_num + 1, total_actions, total_time, started_tasks
                    )
                else:
                    # If there are no further tasks that are not started, calculate the shortest action sequence.
                    # We should calculate all cases according to the order of finishing tasks in started_tasks.
                    min_time = int('inf')
                    best_action_sequence = []

                    for finish_order in permutations(started_tasks):
                        temp_actions = []
                        temp_time = 0
                        current_node = updated_node
                        temp_queue = list(started_tasks)

                        for left_time, wait_time, task in finish_order:
                            if wait_time > 0:
                                temp_actions.append(f"wait for {wait_time} time steps")
                                temp_time += wait_time
                                for i in range(len(finish_order)):
                                    finish_order[i][0] -= wait_time; finish_order[i][1] -= wait_time
                            actions, time_taken, updated_node = execute_subtask(G, current_node, task, start=False)
                            temp_actions.extend(actions)
                            temp_time += time_taken

                            

        else:
            actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
            total_actions.extend(actions)
            total_time += time_taken
            heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]][1], TIME_BOUNDARIES[current_task[3]][0], current_task))

            total_actions, total_time = check_feasibility(
                G, updated_node, tasks, task_num + 1, total_actions, total_time, started_tasks
            )

    else:
        breakpoint()

    return total_actions, total_time



def check_feasibility(G, last_node, tasks, task_num, total_actions, total_time, started_tasks):
    # If there are no tasks left to process, return accumulated actions and time
    if task_num >= len(tasks) and not started_tasks:
        return total_actions, total_time
    
    # Identify the current task and the prior task if available
    current_task = tasks[task_num] if task_num < len(tasks) else None

    # Go to the current task's milestone if it exists
    if current_task:
        if len(started_tasks) > 0 :

            actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
            _, time_taken_to_go_back = get_shortest_path_distance(G, updated_node, last_node)

            # Check if starting the next task would exceed the time boundary
            if time_taken + time_taken_to_go_back > started_tasks[0][0]:

                # Complete the task as the time boundary allows
                if started_tasks[0][1] > 0:
                    total_actions.append(f"wait for {started_tasks[0][1]} time steps")
                    total_time += started_tasks[0][1]
                    started_tasks = update_priority_queue(started_tasks, started_tasks[0][1])
                actions, time_taken, updated_node = execute_subtask(G, last_node, started_tasks[0][2], start=False)
                total_actions.extend(actions)
                total_time += time_taken
                started_tasks = update_priority_queue(started_tasks, time_taken)
                _, _, _ = heapq.heappop(started_tasks)

                total_actions_, total_time_ = check_feasibility(G, updated_node, tasks, task_num, total_actions, total_time, started_tasks)
                if total_actions_:
                    total_actions = total_actions_; total_time = total_time_


            else:
                # We can start the new task and add it to the queue of started tasks
                actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
                total_actions.extend(actions)
                total_time += time_taken
                started_tasks = update_priority_queue(started_tasks, time_taken)
                heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]][1], TIME_BOUNDARIES[current_task[3]][0], current_task))

                # If there are further tasks, proceed recursively
                if task_num + 1 < len(tasks):
                    total_actions, total_time = check_feasibility(
                        G, updated_node, tasks, task_num + 1, total_actions, total_time, started_tasks
                    )
                else:
                    # If there are no further tasks that are not started, calculate the shortest action sequence.
                    actions, time_taken, updated_node = calculate_finish_action_sequence(G, started_tasks)



        else:
            actions, time_taken, updated_node = execute_subtask(G, last_node, current_task, start=True)
            total_actions.extend(actions)
            total_time += time_taken
            heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]][1], TIME_BOUNDARIES[current_task[3]][0], current_task))

            total_actions, total_time = check_feasibility(
                G, updated_node, tasks, task_num + 1, total_actions, total_time, started_tasks
            )

    else:
        breakpoint()

    return total_actions, total_time



def calculate_consumed_time(G, subtasks, env, agent):
    total_actions = []; total_time = 0; obj_states = {}
    # Initialize obj_states
    tmp = []
    for subtask in subtasks:
        if not subtask['task_id'] in tmp:
            obj_states[subtask['object_target']] = subtask['desired_state']
            tmp.append(subtask['task_id'])
    
    current_node = 'spawned_location'
    for subtask in subtasks:
        actions, time_taken, updated_node, env = execute_subtask(G, current_node, subtask, env, agent)
        current_node = updated_node
        if actions:
            total_actions.extend(actions)
            total_time += time_taken
        else:
            return 0,0,0




#######################################################################################################
def get_all_permutations(tasks_):
    all_permutations_ = []
    for p in permutations(tasks_):
        perm_list = list(p)
        if perm_list not in all_permutations_:
            all_permutations_.append(perm_list)

    q = []; all_permutations = []
    for i, tasks in enumerate(all_permutations_):
        updated_tasks = []
        for j, task in enumerate(tasks):
            if task['task_id'] not in q:
                task_with_stage = task.copy()
                task_with_stage['stage'] = 'start'
                q.append(task['task_id'])
            else:
                task_with_stage = task.copy()
                task_with_stage['stage'] = 'finish'
                q.remove(task['task_id'])
            updated_tasks.append(task_with_stage)
        all_permutations.append(updated_tasks)
    return all_permutations

# Function to generate the minimum action sequence for each task
def get_shortest_action_sequence(G, subtasks):
    actions, total_time = calculate_consumed_time(G, subtasks, 'spawned_location')
    if actions:
        return actions, total_time   # actions, total_time




#########################################################################################################################################
def save_data():
    print()

def main(args):
    # start THOR
    # env = ThorEnv(save_frames_to_disk=True)
    tasks = []
    env = ThorEnv()
    problems = args.problem
    for _ in trange(len(problems)):
        # load traj_data
        traj_data = []
        root = problems.pop(0)
        print(f"Playing '{root}'.")
        representative_folder = root.split('/')[-1].split('__')[0]
        
        for trial in os.listdir(root):
            if "trial" in trial:
                json_file = os.path.join(root, trial, 'traj_data.json')
                with open(json_file, 'r') as f:
                    data = json.load(f)
                # task = [data['task_type'], data['pddl_params']['object_target'], data['pddl_params']['parent_target'], next(iter(data.get('desired_state', {}).values()), 'None')]
                task = {'task_id': data['task_id'],
                        'task_type': data['task_type'],
                        'object_target': data['pddl_params']['object_target'],
                        'parent_target': data['pddl_params']['parent_target'],
                        'desired_state': next(iter(data.get('desired_state', {}).values()), 'None')}
                # try:
                #     task.append(TIME_THRESHOLDS[task[-1]])
                # except:
                #     task.append(1)
                tasks.append(task)
                tasks.append(task)

                if data['task_type'] in representative_folder and \
                    data['pddl_params']['object_target'] in representative_folder and \
                    data['pddl_params']['parent_target'] in representative_folder:
                    if not data['pddl_params']['object_sliced'] or 'Sliced' in representative_folder:
                        traj_data.insert(0, data)
                        representative_data = data
                        continue
                traj_data.append(data)

        ##########################################
        with open(os.path.join(root,'receps_objects.json')) as f:
            recep_objects = json.load(f)
        # Load layout and recep_objects data
        floorplan = representative_data['scene']['floor_plan']
        layout = np.load('alfworld/gen/layouts/' + floorplan + '-layout.npy')
        layout = {tuple(coord) for coord in layout}  # Convert layout to a set of tuples for quick lookup
        spawned_location = (representative_data['scene']['init_action']['x'], representative_data['scene']['init_action']['z'])
        G = generate_graph(layout, recep_objects, spawned_location)
        ##########################################
        all_permutations = get_all_permutations(tasks)
        candidates = []
        for subtasks in all_permutations:
            setup_scene(env, traj_data, 0, args)
            AgentModule = OracleAgent
            agent = AgentModule(env, traj_data, traj_root=root, load_receps=args.load_receps, debug=args.debug)
            print(agent.feedback)

            actions, total_time, env = calculate_consumed_time(G, subtasks, env, agent)
            if actions:
                candidates.append((total_time, actions))
        candidates = sorted(candidates)
        # calculated near-optimal solution
        action_sequence = candidates[0][1]
        consumed_time = candidates[0][0]
        save_data()






        ##########################################

        for cmd in action_plan:
            agent.step(cmd)
            if not args.debug:
                print(agent.feedback)

            done = env.get_goal_satisfied()
            if done:
                print("You won!")
                break

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
        # json_path = os.path.join(ALFWORLD_DATA, "json_3.0.1")
        # problems = glob.glob(pjoin(json_path, "**", "initial_state.pddl"), recursive=True)

        # # Remove problem which contains movable receptacles.
        # # problems = [p for p in problems if "movable_recep" not in p]

        # # Only Cool taasks
        # # problems = [p for p in problems if "cool" in p]
        # # print(len(problems))

        # # args.problem = os.path.dirname(random.choice(problems))
        # args.problem = problems[0].split('/initial')[0]

        ### json_3.0.3
        json_path = os.path.join(ALFWORLD_DATA, "json_3.0.6/"+args.split)
        problems = [os.path.join(json_path, item) for item in os.listdir(json_path)]
        args.problem = problems

    if "movable_recep" in args.problem:
        raise ValueError("This problem contains movable receptacles, which is not supported by ALFWorld.")

    main(args)

