#!/usr/bin/env python
import re
import os
import sys
import json
import glob
import random
import time
import argparse
from os.path import join as pjoin
from tqdm import trange
import numpy as np
import networkx as nx
from itertools import permutations
import heapq
import copy
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
    'freezing': [TIME_THRESHOLDS['freezing'], int(10e4)],
    'warm': [TIME_THRESHOLDS['warm'], TIME_THRESHOLDS['hot']],
    'hot': [TIME_THRESHOLDS['hot'], TIME_THRESHOLDS['boiling']],
    'boiling': [TIME_THRESHOLDS['boiling'], int(10e4)],
    'rinsed': [TIME_THRESHOLDS['rinsed'], int(10e4)],
    'washed': [TIME_THRESHOLDS['washed'], int(10e4)],
}
# constants
RECEPTACLES = set(constants.RECEPTACLES) | {'Sink', 'Bathtub'}
OBJECTS = (set(constants.OBJECTS_WSLICED) - set(RECEPTACLES)) | set(constants.MOVABLE_RECEPTACLES)
OBJECTS -= {'Blinds', 'Boots', 'Cart', 'Chair', 'Curtains', 'Footstool', 'Mirror', 'LightSwtich', 'Painting', 'Poster', 'ShowerGlass', 'Window'}
STATIC_RECEPTACLES = set(RECEPTACLES) - set(constants.MOVABLE_RECEPTACLES)
OPENABLE_CLASS_LIST = ['Fridge', 'Cabinet', 'Microwave', 'Drawer', 'Safe', 'Box']

#########################################################################################################################################
def setup_scene(env, traj_data, r_idx, args, representative_datapath, reward_type='dense'):
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

#########################################################################################################################################
def generate_graph(layout, recep_objects, spawned_location=False):
    # Sample recep_objects for demonstration
    # recep_objects = {
    #     "diningtable 1": {
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
    # node_data = {}
    # for key, value in recep_objects.items():
    #     node_data[value["num_id"]] = value
    node_data = recep_objects

    # Initialize graph
    G = nx.Graph()

    # Add nodes to the graph
    for node_id, info in node_data.items():
        G.add_node(node_id, object_type=info['object_type'], pos=(info['locs']['x'], info['locs']['z']), visible_objects=info['visible_objects'])
        # G.add_node(node_id, object_type=info['object_type'], pos=(info['locs']['x'], info['locs']['z']), visible_objects=info['visible_objects'], objects_inside=info['objects_inside'])
    if spawned_location: G.add_node('spawned_location', object_type='spawned_location', pos=spawned_location, visible_objects = [])

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

class ExecutionError(Exception):
    """Custom exception for execution errors."""
    def __init__(self, message, command=None):
        super().__init__(message)
        self.command = command
        
class TaskExecutor:
    def __init__(self, G, env, agent):
        self.G = G
        self.env = env
        self.agent = agent
        self.current_node = 'spawned_location'
        self.target_obj_instances = {}
        self.used_target_objs = []
        self.total_actions = []
    ###########################################################################################################################

    def execute(self, subtask, cmd):
        action = [cmd, self.env.steps_taken, subtask.copy()]
        self.total_actions.append(action)
        print(cmd)
        self.agent.step(cmd)
        print(self.agent.feedback)
        if "Nothing happens." in self.agent.feedback:
            raise ExecutionError("Execution failed due to "+ cmd)
        
    def remove_inventory_object_in_visible_objects(self):
        for node, attributes in self.G.nodes(data=True):
            # if attributes.get('pos') == self.G.nodes[self.current_node]['pos']:
                visible_objects = attributes.get('visible_objects', [])
                object_to_remove = self.agent.inventory[0]
                if object_to_remove in visible_objects:
                    self.G.nodes[node]['visible_objects'].remove(object_to_remove)
    
    def start_heating(self, subtask):
        try:
            target_obj = subtask['object_target']

            next_node, error_message = self.get_shortest_path_distance(self.current_node, target_obj, new_target=True)
            if not next_node: return error_message

            self.execute(subtask, "go to " + next_node)
            # if "Nothing happens" in self.agent.feedback:
            #     return None
            self.current_node = next_node

            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "open "+self.current_node)
            instances = self.find_instances(self.agent.feedback, target_obj)
            target_obj_instance = instances[0]
            self.used_target_objs.append(target_obj_instance)
            # self.target_obj_instances.append(target_obj_instance)
            
            self.execute(subtask, "take " + target_obj_instance + " from " + self.current_node)
            if "Nothing happens" in self.agent.feedback:
                return None
            target_obj_instance = [target_obj_instance, self.env.last_action['objectId']]
            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "close "+self.current_node)
                
            # for visible_object in self.G.nodes[self.current_node]['visible_objects']:
            #     if visible_object.split(' ')[0] == target_obj:
            #         self.G.nodes[self.current_node]['visible_objects'].remove(visible_object)
            #         break
            # visible_objects = self.agent.update_visible_objects(self.current_node)
            # self.G.nodes[self.current_node]['visible_objects'] = visible_objects
            # self.G.nodes[self.current_node]['visible_objects'].remove(self.agent.inventory[0])
            self.remove_inventory_object_in_visible_objects()
                    
            next_node, error_message = self.get_shortest_path_distance(self.current_node, 'microwave 1')
            if not next_node: return error_message
            self.execute(subtask, "go to microwave 1")
            # if "Nothing happens" in self.agent.feedback:
            #     return None
            self.current_node = next_node
            
            self.execute(subtask, "open microwave 1")
            self.execute(subtask, "put " + target_obj_instance[0] + " in microwave 1")
            self.execute(subtask, "close microwave 1")
            self.execute(subtask, "toggle on microwave 1")
            return target_obj_instance
        
        except Exception as e:
            return e
        except ExecutionError as e:
            return e.command
    
    def start_cooling(self, subtask):
        try:
            target_obj = subtask['object_target']

            next_node, error_message = self.get_shortest_path_distance(self.current_node, target_obj, new_target=True)
            if not next_node: return error_message

            self.execute(subtask, "go to " + next_node)
            # if "Nothing happens" in self.agent.feedback:
            #     return None
            self.current_node = next_node

            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "open "+self.current_node)
            instances = self.find_instances(self.agent.feedback, target_obj)
            target_obj_instance = instances[0]
            self.used_target_objs.append(target_obj_instance)
            self.execute(subtask, "take " + target_obj_instance + " from " + self.current_node)
            if "Nothing happens" in self.agent.feedback:
                return None
            target_obj_instance = [target_obj_instance, self.env.last_action['objectId']]
            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "close "+self.current_node)
            
            # self.G.nodes[self.current_node]['visible_objects'].remove(self.agent.inventory[0])
            self.remove_inventory_object_in_visible_objects()

            next_node, error_message = self.get_shortest_path_distance(self.current_node, 'fridge 1')
            if not next_node: return error_message
            self.execute(subtask, "go to fridge 1")
            # if "Nothing happens" in self.agent.feedback:
            #     return None
            self.current_node = next_node

            self.execute(subtask, "open fridge 1")

            self.execute(subtask, "put " + target_obj_instance[0] + " in fridge 1")

            self.execute(subtask, "close fridge 1")

            return target_obj_instance
        except Exception as e:
            return e

    def start_cleaning(self, subtask):
        try:
            target_obj = subtask['object_target']

            next_node, error_message = self.get_shortest_path_distance(self.current_node, target_obj, new_target=True)
            if not next_node: return error_message

            self.execute(subtask, "go to " + next_node)
            # if "Nothing happens" in self.agent.feedback:
            #     return None
            self.current_node = next_node

            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "open "+self.current_node)
            instances = self.find_instances(self.agent.feedback, target_obj)
            target_obj_instance = instances[0]
            self.used_target_objs.append(target_obj_instance)
            self.execute(subtask, "take " + target_obj_instance + " from " + self.current_node)

            target_obj_instance = [target_obj_instance, self.env.last_action['objectId']]
            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "close "+self.current_node)

            # for visible_object in self.G.nodes[self.current_node]['visible_objects']:
            #     if visible_object.split(' ')[0] == target_obj:
            #         self.G.nodes[self.current_node]['visible_objects'].remove(visible_object)
            #         break
            # visible_objects = self.agent.update_visible_objects(self.current_node)
            # self.G.nodes[self.current_node]['visible_objects'] = visible_objects
            # self.G.nodes[self.current_node]['visible_objects'].remove(self.agent.inventory[0])
            self.remove_inventory_object_in_visible_objects()

            next_node, error_message = self.get_shortest_path_distance(self.current_node, 'sinkbasin 1')
            if not next_node: return error_message
            self.execute(subtask, "go to sinkbasin 1")

            self.current_node = next_node

            self.execute(subtask, "put " + target_obj_instance[0] + " in sinkbasin 1")

            self.execute(subtask, "toggle on faucet 1")

            return target_obj_instance
        except Exception as e:
            return e


    def finish_heating(self, subtask):
        try:
            target_obj = subtask['object_target']
            parent_obj = subtask['parent_target']
            target_obj_instance = self.target_obj_instances[subtask['task_id']]

            if self.current_node != 'microwave 1':
                next_node, error_message = self.get_shortest_path_distance(self.current_node, 'microwave 1')
                if not next_node: return error_message
                self.execute(subtask, "go to microwave 1")
                self.current_node = next_node

            heated_time = self.env.object_states[target_obj_instance[1]]['heated_time']
            if heated_time < TIME_BOUNDARIES[subtask['desired_state']][0]:
                self.execute(subtask, "wait for " + str(TIME_BOUNDARIES[subtask['desired_state']][0] - heated_time) + " time steps")
            # elif heated_time > TIME_BOUNDARIES[subtask['desired_state']][1]:
            #     return None

            self.execute(subtask, "toggle off microwave 1")

            self.execute(subtask, "open microwave 1")

            self.execute(subtask, "take " + target_obj_instance[0] + " from microwave 1")

            self.execute(subtask, "close microwave 1")

            next_node, error_message = self.get_shortest_path_distance(self.current_node, parent_obj)
            if not next_node: return error_message
            self.execute(subtask, "go to " + next_node)
            self.current_node = next_node

            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "open "+self.current_node)
            self.execute(subtask, "put " + target_obj_instance[0] + " on/in " + self.current_node)
            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "close "+self.current_node)

            visible_objects = self.agent.update_visible_objects(self.current_node)
            self.G.nodes[self.current_node]['visible_objects'] = visible_objects

            return True
        except Exception as e:
            return e
    
    def finish_cooling(self, subtask):
        try:
            target_obj = subtask['object_target']
            parent_obj = subtask['parent_target']
            target_obj_instance = self.target_obj_instances[subtask['task_id']]

            if self.current_node != 'fridge 1':
                next_node, error_message = self.get_shortest_path_distance(self.current_node, 'fridge 1')
                if not next_node: return error_message
                self.execute(subtask, "go to " + next_node)
                self.current_node = next_node

            cooled_time = self.env.object_states[target_obj_instance[1]]['cooled_time']
            if cooled_time < TIME_BOUNDARIES[subtask['desired_state']][0]:
                self.execute(subtask, "wait for " + str(TIME_BOUNDARIES[subtask['desired_state']][0] - cooled_time) + " time steps")
            # elif cooled_time > TIME_BOUNDARIES[subtask['desired_state']][1]:
            #     return None

            self.execute(subtask, "open fridge 1")

            self.execute(subtask, "take " + target_obj_instance[0] + " from fridge 1")

            self.execute(subtask, "close fridge 1")

            next_node, error_message = self.get_shortest_path_distance(self.current_node, parent_obj)
            if not next_node: return error_message
            self.execute(subtask, "go to " + next_node)
            self.current_node = next_node

            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "open "+self.current_node)
            self.execute(subtask, "put " + target_obj_instance[0] + " on/in " + self.current_node)
            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "close "+self.current_node)
            
            visible_objects = self.agent.update_visible_objects(self.current_node)
            self.G.nodes[self.current_node]['visible_objects'] = visible_objects

            return True
        except Exception as e:
            return e


    def finish_cleaning(self, subtask):
        try:
            target_obj = subtask['object_target']
            parent_obj = subtask['parent_target']
            target_obj_instance = self.target_obj_instances[subtask['task_id']]

            if self.current_node != 'sinkbasin 1':
                next_node, error_message = self.get_shortest_path_distance(self.current_node, 'sinkbasin 1')
                if not next_node: return error_message
                self.execute(subtask, "go to sinkbasin 1")
                self.current_node = next_node

            cleaned_time = self.env.object_states[target_obj_instance[1]]['cleaned_time']
            if cleaned_time < TIME_BOUNDARIES[subtask['desired_state']][0]:
                self.execute(subtask, "wait for " + str(TIME_BOUNDARIES[subtask['desired_state']][0] - cleaned_time) + " time steps")
            elif cleaned_time > TIME_BOUNDARIES[subtask['desired_state']][1]:
                return None

            self.execute(subtask, "toggle off faucet 1")

            self.execute(subtask, "take " + target_obj_instance[0] + " from sinkbasin 1")
            
            next_node, error_message = self.get_shortest_path_distance(self.current_node, parent_obj)
            if not next_node:
                return error_message
            self.execute(subtask, "go to " + next_node)
            self.current_node = next_node


            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "open "+self.current_node)
            self.execute(subtask, "put " + target_obj_instance[0] + " on/in " + self.current_node)
            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "close "+self.current_node)

            visible_objects = self.agent.update_visible_objects(self.current_node)
            self.G.nodes[self.current_node]['visible_objects'] = visible_objects
            return True
        except Exception as e:
            return e


    def start_simple(self, subtask):
        try:
            target_obj = subtask['object_target']

            next_node, error_message = self.get_shortest_path_distance(self.current_node, target_obj, new_target=True)
            if not next_node: return error_message

            self.execute(subtask, "go to " + next_node)
            if "Nothing happens" in self.agent.feedback:
                return None
            self.current_node = next_node

            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "open "+self.current_node)
            instances = self.find_instances(self.agent.feedback, target_obj)
            target_obj_instance = instances[0]
            self.used_target_objs.append(target_obj_instance)
            self.execute(subtask, "take " + target_obj_instance + " from " + self.current_node)
            if "Nothing happens" in self.agent.feedback:
                return None
            target_obj_instance = [target_obj_instance, self.env.last_action['objectId']]
            # if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
            #     self.execute(subtask, "close "+self.current_node)
            # self.G.nodes[self.current_node]['visible_objects'].remove(self.agent.inventory[0])
            self.remove_inventory_object_in_visible_objects()

            return target_obj_instance
        except Exception as e:
            return e

    def finish_simple(self, subtask):
        try:
            target_obj = subtask['object_target']
            parent_obj = subtask['parent_target']
            target_obj_instance = self.target_obj_instances[subtask['task_id']]

            next_node, error_message = self.get_shortest_path_distance(self.current_node, parent_obj)
            if not next_node: return error_message
            if self.current_node != next_node:
                self.execute(subtask, "go to "+next_node)
                self.current_node = next_node

            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "open "+self.current_node)
            self.execute(subtask, "put " + target_obj_instance[0] + " on/in " + self.current_node)
            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "close "+self.current_node)

            visible_objects = self.agent.update_visible_objects(self.current_node)
            self.G.nodes[self.current_node]['visible_objects'] = visible_objects

            return True
        except Exception as e:
            return e
        
    def complete_simple(self, subtask):
        try:
            # start
            target_obj = subtask['object_target']
            parent_obj = subtask['parent_target']

            next_node, error_message = self.get_shortest_path_distance(self.current_node, target_obj, new_target=True)
            if not next_node: return error_message

            self.execute(subtask, "go to " + next_node)
            if "Nothing happens" in self.agent.feedback:
                return None
            self.current_node = next_node

            instances = self.find_instances(self.agent.feedback, target_obj)
            target_obj_instance = instances[0]
            self.used_target_objs.append(target_obj_instance)
            self.execute(subtask, "take " + target_obj_instance + " from " + self.current_node)
            if "Nothing happens" in self.agent.feedback:
                return None
            target_obj_instance = [target_obj_instance, self.env.last_action['objectId']]
            self.remove_inventory_object_in_visible_objects()

            self.target_obj_instances[subtask['task_id']] = target_obj_instance

            # finish
            target_obj_instance = self.target_obj_instances[subtask['task_id']]

            next_node, error_message = self.get_shortest_path_distance(self.current_node, parent_obj)
            if not next_node: return error_message
            if self.current_node != next_node:
                self.execute(subtask, "go to "+next_node)
                self.current_node = next_node

            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "open "+self.current_node)
            self.execute(subtask, "put " + target_obj_instance[0] + " on/in " + self.current_node)
            if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                self.execute(subtask, "close "+self.current_node)

            visible_objects = self.agent.update_visible_objects(self.current_node)
            self.G.nodes[self.current_node]['visible_objects'] = visible_objects

            return True

        except Exception as e:
            return e


    def test_valid_position(self, target_objects, parent_objects, layout):
        try:
            for idx, parent_object in enumerate(parent_objects):
                target_object = target_objects[idx]
                # go to target object
                next_node, error_message = self.get_shortest_path_distance(self.current_node, target_object, new_target=True)
                if not next_node: return False, error_message
                self.agent.step("go to " + next_node)
                self.current_node = next_node
                
                instances = self.find_instances(self.agent.feedback, target_object)
                if len(instances) == 0:
                    for obj in self.G.nodes[self.current_node]['visible_objects']:
                        if target_object.lower() in obj:
                            instances.append(obj)
                            break
                target_obj_instance = instances[0]
                # self.used_target_objs.append(target_obj_instance)
                if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                    self.agent.step("open "+self.current_node)
                self.agent.step("take " + target_obj_instance + " from " + self.current_node)
                if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                    self.agent.step("close "+self.current_node)
                    
                # self.agent.receptacles = {}; self.agent.receptacles_instance_id = {}; self.agent.objects = {}
                # self.agent.explore_scene()
                # G = generate_graph(layout, self.agent.receptacles_instance_id); self.G = G
                # self.agent.step("go to " + self.current_node)
                
                # visible_objects = self.agent.update_visible_objects(self.current_node)
                # self.G.nodes[self.current_node]['visible_objects'] = visible_objects
                
                next_node, error_message = self.get_shortest_path_distance(self.current_node, parent_object)
                if not next_node: return False, error_message
                self.agent.step("go to " + next_node)
                self.current_node = next_node


                if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                    self.agent.step("open "+self.current_node)
                self.agent.step("put " + target_obj_instance + " on/in " + self.current_node)
                if "Nothing happens" in self.agent.feedback:
                    raise ExecutionError(self.env.last_event.metadata['errorMessage'])
                    # raise False, self.env.last_event.metadata['errorMessage']
                if self.current_node.split(' ')[0].capitalize() in OPENABLE_CLASS_LIST:
                    self.agent.step("close "+self.current_node)

                # visible_objects = self.agent.update_visible_objects(self.current_node)
                # self.G.nodes[self.current_node]['visible_objects'] = visible_objects
                
                # self.agent.receptacles = {}; self.agent.receptacles_instance_id = {}; self.agent.objects = {}
                self.agent.update_visible_objects_all()
                G = generate_graph(layout, self.agent.receptacles_instance_id); self.G = G
                self.G.nodes[self.current_node]['visible_objects'].append(target_obj_instance)
                # self.agent.step("go to " + self.current_node)
            return True, ""
                
                
        except Exception as e:
            return False, e
            





    def execute_subtask(self, subtask):
        if subtask['task_type'] in ["pick_and_place_simple", "pick_two_obj_and_place"]:
            result = self.complete_simple(subtask)
            if isinstance(result, Exception) or isinstance(result, ExecutionError) or isinstance(result, str):
                return result

        else:
            if subtask['stage'] == 'start':
                if subtask['task_type'] in ["pick_cool_then_place_in_recep", "pick_heat_then_place_in_recep", "pick_clean_then_place_in_recep"]:
                    start_task = getattr(self, f"start_{subtask['task_type'].split('_')[1]}ing")
                target_obj_instance = start_task(subtask)
                if isinstance(target_obj_instance, Exception) or isinstance(target_obj_instance, ExecutionError) or isinstance(target_obj_instance, str):
                    return target_obj_instance
                else:
                    self.target_obj_instances[subtask['task_id']] = target_obj_instance
            else:
                if subtask['task_type'] in ["pick_cool_then_place_in_recep", "pick_heat_then_place_in_recep", "pick_clean_then_place_in_recep"]:
                    finish_task = getattr(self, f"finish_{subtask['task_type'].split('_')[1]}ing")
                result = finish_task(subtask)
                if isinstance(result, Exception) or isinstance(result, ExecutionError) or isinstance(result, str):
                    return result

        return True

    def calculate_consumed_time(self, subtasks):
        for subtask in subtasks:
            result = self.execute_subtask(subtask)
            if isinstance(result, Exception)or isinstance(result, ExecutionError) or isinstance(result, str):
                if self.env.last_event.metadata['errorMessage'] != "":
                    result = self.env.last_event.metadata['errorMessage']
                return result, 0, self.env
        return self.total_actions, self.env.steps_taken, self.env

    def get_shortest_path_distance(self, start_node, object_target, new_target=False):
        # if object_target is the node name (e.g., fridge 1)
        if object_target in self.G.nodes():
            return object_target, nx.shortest_path_length(self.G, start_node, object_target, weight='weight')

        # if object_target is receptacle
        if object_target in STATIC_RECEPTACLES:
            target_nodes = []
            for node, data in self.G.nodes(data=True):
                if data['object_type'] == object_target:
                    target_nodes.append(node)
        else:
            # Iterate through all nodes to find nodes containing the object_target in visible_objects
            target_nodes = []
            for node, data in self.G.nodes(data=True):
                visible_objects = data.get('visible_objects', [])
                # Check if the object_target is in any of the visible_objects
                for obj in visible_objects:
                    if obj.split(' ')[0] == object_target.lower():
                        if not new_target or obj not in self.used_target_objs:
                            target_nodes.append(node)
                            break

        # If no nodes contain the target object, return None
        if not target_nodes:
            # Address when the object is not found in any visible objects
            
            # for node, data in self.G.nodes(data=True):
            #     objects_inside = data.get('objects_inside', [])
            #     # Check if the object_target is in any of the objects_inside
            #     for obj in objects_inside:
            #         if obj.split(' ')[0] == object_target.lower():
            #             target_nodes.append(node)
            #             break
            
            print(f"Object '{object_target}' not found in any visible objects.")
            return 0, f"Object '{object_target}' not found in any visible objects."

        # Calculate shortest path distance to the nearest node containing the target object
        shortest_distance = float('inf')
        closest_node = None
        for target_node in target_nodes:
            try:
                distance = nx.shortest_path_length(self.G, start_node, target_node, weight='weight')
                if distance < shortest_distance:
                    shortest_distance = distance
                    closest_node = target_node
            except nx.NetworkXNoPath:
                # If there's no path between start_node and target_node, continue
                continue

        # Return the closest node and shortest distance
        if closest_node:
            # print(f"Closest node containing '{object_target}': {closest_node} with distance {shortest_distance}")
            return closest_node, shortest_distance
        else:
            # print(f"No reachable node found for object '{object_target}'")target_obj_instance
            return 0, f"No reachable node found for object '{object_target}'"

    def find_instances(self, input_text, target_obj):
        pattern = rf"\b{target_obj.lower()} \d+\b"
        instances = re.findall(pattern, input_text.lower())
        target_objs = self.used_target_objs
        instances = [i for i in instances if i not in target_objs]
        return instances








#########################################################################################################################################
def get_all_permutations(tasks_):
    all_permutations_ = []
    for p in permutations(tasks_):
        perm_list = list(p)
        if perm_list not in all_permutations_:
            all_permutations_.append(perm_list)

    all_permutations = []
    for tasks in all_permutations_:
        q = []; updated_tasks = []
        for task in tasks:
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
#########################################################################################################################################
def save_data(action_sequence, consumed_time, root):
    result = {'action_sequence': action_sequence, 'consumed_time': consumed_time}
    with open(os.path.join(root, 'expert_demo.json'), 'w') as f:
        json.dump(result,f,indent=4)
    print()
def check_visible_in_env(env, traj_data, G, task_executor, layout):
    ## Check if any target obeject is only in the openable receptacles
    # target_objects_v = [target for t in traj_data for target in ([t['pddl_params']['object_target']] * (2 if 'two' in t['task_type'] else 1))]
    target_objects_v = []
    # parent_objects = [parent for t in traj_data for parent in ([t['pddl_params']['parent_target']] * (2 if 'two' in t['task_type'] else 1))]
    target_objects = []; parent_objects = []

    for data in traj_data:
        target_objects.append(data['pddl_params']['object_target']); parent_objects.append(data['pddl_params']['parent_target'])
        target_objects_v.append(data['pddl_params']['object_target'])
        if 'two' in data['task_type']:
            target_objects.append(data['pddl_params']['object_target']); parent_objects.append(data['pddl_params']['parent_target'])
            target_objects_v.append(data['pddl_params']['object_target']+'_two')
        if 'clean' in data['task_type']:
            target_objects.append(data['pddl_params']['object_target']); parent_objects.append('SinkBasin')
        if 'cool' in data['task_type']:
            target_objects.append(data['pddl_params']['object_target']); parent_objects.append('Fridge')
        if 'heat' in data['task_type']:
            target_objects.append(data['pddl_params']['object_target']); parent_objects.append('Microwave')
        
    
    forceVisible = False
    used_target_objs = []
    for object_target in target_objects_v:
        # Iterate through all nodes to find nodes containing the object_target in visible_objects
        found = False
        for node, data in G.nodes(data=True):
            if found: break
            visible_objects = data.get('visible_objects', [])
            # Check if the object_target is in any of the visible_objects
            for obj in visible_objects:
                if '_two' in object_target.lower():
                    object_target = object_target.split('_two')[0]
                    if obj.split(' ')[0] == object_target.lower():
                        # if obj not in used_target_objs:
                            used_target_objs.append(obj)
                            found = True
                            break                
                elif obj.split(' ')[0] == object_target.lower():
                    if obj not in used_target_objs:
                        # used_target_objs.append(obj)
                        found = True
                        break

        # If no nodes contain the target object, return None
        if not found:
            forceVisible = True; print("no visible objects in env")
            return forceVisible, env
    
    valid, error = task_executor.test_valid_position(target_objects, parent_objects, layout)
    if not valid:
        print(str(error))
        return True, env  
    return forceVisible, env
    
    
    # for target_object in target_objects:
    #     visible = []
    #     for data in objects:
    #         if data['objectType'] == target_object:
    #             try:
    #                 found = False
    #                 for recep in data['parentReceptacles']:
    #                     if recep.split('|')[0] not in OPENABLE_CLASS_LIST:
    #                         visible.append(1)
    #                         objects.remove(data)
    #                         found = True
    #                         break
    #                 if found: break
    #             except: pass
    #     if 1 not in visible:
    #         forceVisible = True
    #         break
    # return forceVisible, env
#########################################################################################################################################

def main(args):
    no_solution = []
    env = ThorEnv()
    problems = args.problem
    for i in trange(len(problems)):
        
        tasks = []
        traj_data = []
        root = problems[i]
        if os.path.exists(os.path.join(root, 'expert_demo.json')):
            print("=========== expert_demo exists ===========")
            continue
        print(f"\nPlaying '{root}'.")
        representative_folder = root.split('/')[-1].split('__')[0]
        # no_solution[str(i+int(args.start_idx))] = {'root':root, 'error_messages':[]}

        for trial in os.listdir(root):
            if "trial" in trial:
                json_file = os.path.join(root, trial, 'traj_data.json')
                with open(json_file, 'r') as f:
                    data = json.load(f)
                task = {'task_id': data['task_id'],
                        'task_type': data['task_type'],
                        'object_target': data['pddl_params']['object_target'],
                        'parent_target': data['pddl_params']['parent_target'],
                        'desired_state': next(iter(data.get('desired_state', {}).values()), 'None')}
                if task['task_type'] != 'pick_and_place_simple':
                    tasks.append(task)
                tasks.append(task)
                # if data['task_type'] == "pick_two_obj_and_place":
                #     tasks.append(task)
                #     tasks.append(task)    

                if data['task_type'] in representative_folder and \
                        data['pddl_params']['object_target'] in representative_folder and \
                        data['pddl_params']['parent_target'] in representative_folder:
                    if not data['pddl_params']['object_sliced'] or 'Sliced' in representative_folder:
                        traj_data.insert(0, data)
                        representative_datapath = json_file
                        continue
                traj_data.append(data)
        ###########################################################################################################################################
        representative_data = traj_data[0]
        
        scene_num = traj_data[0]['scene']['scene_num']
        object_poses = traj_data[0]['scene']['object_poses']
        dirty_and_empty = traj_data[0]['scene']['dirty_and_empty']
        object_toggles = traj_data[0]['scene']['object_toggles']

        scene_name = 'FloorPlan%d' % scene_num
        env.reset(scene_name)
        env.restore_scene(object_poses, object_toggles, dirty_and_empty)

        # initialize to start position
        env.step(dict(data['scene']['init_action']))
    
        floorplan = representative_data['scene']['floor_plan']
        layout = np.load('alfworld/gen/layouts/' + floorplan + '-layout.npy')
        layout = {tuple(coord) for coord in layout}
        spawned_location = (representative_data['scene']['init_action']['x'], representative_data['scene']['init_action']['z'])
        # G = generate_graph(layout, recep_objects, spawned_location)
        if spawned_location not in layout:
            spawned_location = random.choice(list(layout))
            traj_data[0]['scene']['init_action']['x'] = spawned_location[0]
            traj_data[0]['scene']['init_action']['z'] = spawned_location[1]
            with open(representative_datapath, 'w') as f:
                json.dump(traj_data[0],f,indent=4)
    
        target_objects = [target for t in traj_data for target in ([t['pddl_params']['object_target']])]
        parent_objects = [parent for t in traj_data for parent in ([t['pddl_params']['parent_target']])]
        if 'pick_clean_then_place_in_recep' in [data['task_type'] for data in traj_data]: parent_objects.append('SinkBasin'); parent_objects.append('Sink')
        if 'pick_cool_then_place_in_recep' in [data['task_type'] for data in traj_data]: parent_objects.append('Fridge')
        if 'pick_heat_then_place_in_recep' in [data['task_type'] for data in traj_data]: parent_objects.append('Microwave')
        numRepeats = [{'objectType': obj, 'count': 2} for obj in target_objects]
        minFreePerReceptacleType = [{'objectType': obj, 'count': 1000000} for obj in parent_objects]
    
        # env.step(dict(action = 'InitialRandomSpawn', forceVisible = True, numRepeats = numRepeats, minFreePerReceptacleType = minFreePerReceptacleType))
    
        nochanged = True; forceVisible = False
        for k in range(25):
            AgentModule = OracleAgent
            agent = AgentModule(env, traj_data, traj_root=root, load_receps=args.load_receps, debug=args.debug)
            agent.receptacles = {}; agent.receptacles_instance_id = {}; agent.objects = {}
            agent.explore_scene()
            G = generate_graph(layout, agent.receptacles_instance_id, spawned_location)
            task_executor = TaskExecutor(G, env, agent)
            forceVisible, env = check_visible_in_env(env, traj_data, G, task_executor, layout)
            if forceVisible:
                env.reset(scene_name)
                env.step(dict(action = 'InitialRandomSpawn', randomSeed = k, forceVisible = True, numRepeats = numRepeats, minFreePerReceptacleType = minFreePerReceptacleType))
                new_objects = []
                for obj in env.last_event.metadata['objects']:
                    new_objects.append({'objectName': obj['name'].split('(Clone)')[0], 'position': obj['position'], 'rotation': obj['rotation']})
                traj_data[0]['scene']['object_poses'] = new_objects
                nochanged = False
            else:
                if nochanged: break
                # traj_data[0]['scene']['object_poses'] = new_objects
                with open(representative_datapath, 'w') as f:
                    json.dump(traj_data[0],f,indent=4)
                break
        if forceVisible:
            last_error = "Cannot make posible environments (no valid positions or not enough visible objects)"
            no_solution.append([str(i+int(args.start_idx)), root, last_error])
        ###########################################################################################################################################
        else:

            all_permutations = get_all_permutations(tasks)
            all_permutations.reverse()
            candidate = (float('inf'), None)
            last_error = ""
            for j in trange(len(all_permutations), desc="Processing Permutations"):
                subtasks = all_permutations[j]
                # if candidate[0] == float('inf') and j>(len(all_permutations)/2): 
                #     break
                print()
                setup_scene(env, traj_data, 0, args, representative_datapath)
                AgentModule = OracleAgent
                agent = AgentModule(env, traj_data, traj_root=root, load_receps=args.load_receps, debug=args.debug)
                print(agent.feedback)                
                G = generate_graph(layout, agent.receptacles_instance_id, spawned_location)
                task_executor = TaskExecutor(G, env, agent)
                init_action = dict(traj_data[0]['scene']['init_action'])
                init_action['time'] = 0
                env.step(init_action)
                actions, total_time, env = task_executor.calculate_consumed_time(subtasks)
                if isinstance(actions, Exception) or isinstance(actions, str):
                    # no_solution[str(i+int(args.start_idx))]['error_messages'].append(str(actions))
                    print('Error: ', str(actions))
                    last_error = str(actions)
                else:
                    if env.get_goal_satisfied():
                        candidate = min(candidate, (total_time, actions), key=lambda x: x[0])
                        print("===================== total time: ",str(total_time)," =====================\n")
                    else:
                        print("Goal is not satisfied")

            # calculated near-optimal solution
            action_sequence = candidate[1]
            consumed_time = candidate[0]
            if candidate[0] == float('inf'):
                no_solution.append([str(i+int(args.start_idx)), root, last_error])
            else:
                save_data(action_sequence, consumed_time, root)

        with open(os.path.join(root.split(args.split)[0], args.split, 'no_solution_list_'+str(args.start_idx)+'_'+str(args.end_idx)+'_.json'), 'w') as f:
            json.dump(no_solution,f,indent=4)




        ##########################################

        # for cmd in action_plan:
        #     agent.step(cmd)
        #     if not args.debug:
        #         print(agent.feedback)

        #     done = env.get_goal_satisfied()
        #     if done:
        #         print("You won!")
        #         break

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
    parser.add_argument('--start_idx', type=str)
    parser.add_argument('--end_idx', type=str)
    args = parser.parse_args()

    if args.problem is None:
        ### json_3.0.7
        # len(valid_seen) = 72
        # len(valid_unseen) = 100
        # len(train) = 5171
        
        ### json_3.0.8
        # len(valid_seen) = 66
        # len(valid_unseen) = 87
        # len(train) = 4463
        
        ### json_3.0.9
        # len(valid_seen) = 66
        # len(valid_unseen) = 87
        # len(train) = 2376
        # len(train_3tasks) = 650
               
        
        json_path = os.path.join(ALFWORLD_DATA, "json_3.0.8/"+args.split)
        problems = [os.path.join(json_path, item) for item in os.listdir(json_path)]
        problems = sorted(problems)
        args.problem = problems[int(args.start_idx):int(args.end_idx)]
        print("Problem ", args.start_idx, " to ", args.end_idx, "\n")

    if "movable_recep" in args.problem:
        raise ValueError("This problem contains movable receptacles, which is not supported by ALFWorld.")

    main(args)

