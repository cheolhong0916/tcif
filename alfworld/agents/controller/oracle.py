import os
import cv2
import sys
import json
import re
import random
import traceback

import numpy as np
from collections import Counter

import alfworld.gen
import alfworld.gen.constants as constants
from alfworld.agents.controller.base import BaseAgent
from alfworld.agents.utils.misc import extract_admissible_commands_with_heuristics


class OracleAgent(BaseAgent):

    def __init__(self, env, traj_data, traj_root,
                 load_receps=False, debug=False,
                 goal_desc_human_anns_prob=0.0,
                 use_gt_relations=False):
        self.openable_points = self.get_openable_points(traj_data)
        self.use_gt_relations = use_gt_relations
        self.exploration_frames = []
        super().__init__(env, traj_data, traj_root,
                         load_receps=load_receps, debug=debug,
                         goal_desc_human_anns_prob=goal_desc_human_anns_prob)

    def get_openable_points(self, traj_data):
        scene_num = traj_data[0]['scene']['scene_num']
        openable_json_file = os.path.join(alfworld.gen.__path__[0], 'layouts/FloorPlan%d-openable.json' % scene_num)
        with open(openable_json_file, 'r') as f:
            openable_points = json.load(f)
        return openable_points

    def get_obj_cls_from_metadata(self, name):
        objs = [obj for obj in self.env.last_event.metadata['objects'] if obj['visible'] and name in obj['objectType']]
        return objs[0] if len(objs) > 0 else None

    def get_obj_id_from_metadata(self, object_id):
        objs = [obj for obj in self.env.last_event.metadata['objects'] if object_id == obj['objectId']]
        return objs[0] if len(objs) > 0 else None

    def get_num_interactable_objs(self, recep_id):
        return len([obj for obj in self.env.last_event.metadata['objects'] if obj['visible'] and obj['parentReceptacles'] and recep_id in obj['parentReceptacles']])

    def get_exploration_frames(self):
        return self.exploration_frames

    # # use pre-computed openable points from ALFRED to store receptacle locations
    # def explore_scene(self):
    #     agent_height = self.env.last_event.metadata['agent']['position']['y']
    #     for object_id, point in self.openable_points.items():
    #         action = {'action': 'TeleportFull',
    #                   'x': point[0],
    #                   'y': agent_height,
    #                   'z': point[1],
    #                   'rotateOnTeleport': False,
    #                   'rotation': point[2],
    #                   'horizon': point[3]}
    #         event = self.env.step(action)

    #         if event.metadata['lastActionSuccess']:
    #             self.exploration_frames.append(np.array(self.env.last_event.frame[:,:,::-1]))
    #             instance_segs = np.array(self.env.last_event.instance_segmentation_frame)
    #             color_to_object_id = self.env.last_event.color_to_object_id

    #             # find unique instance segs
    #             color_count = Counter()
    #             for x in range(instance_segs.shape[0]):
    #                 for y in range(instance_segs.shape[1]):
    #                     color = instance_segs[y, x]
    #                     color_count[tuple(color)] += 1

    #             for color, num_pixels in color_count.most_common():
    #                 if color in color_to_object_id:
    #                     object_id = color_to_object_id[color]
    #                     object_type = object_id.split('|')[0]
    #                     if "Basin" in object_id:
    #                         object_type += "Basin"

    #                     if object_type in self.STATIC_RECEPTACLES:
    #                         if object_id not in self.receptacles:
    #                             self.receptacles[object_id] = {
    #                                 'object_id': object_id,
    #                                 'object_type': object_type,
    #                                 'locs': action,
    #                                 'num_pixels': num_pixels,
    #                                 'num_id': "%s %d" % (object_type.lower(), self.get_next_num_id(object_type, self.receptacles)),
    #                                 'closed': True if object_type in constants.OPENABLE_CLASS_LIST else None
    #                             }
    #                         elif object_id in self.receptacles and num_pixels > self.receptacles[object_id]['num_pixels']:
    #                             self.receptacles[object_id]['locs'] = action  # .append(action)
    #                             self.receptacles[object_id]['num_pixels'] = num_pixels

    #     # self.save_receps()


    ############################################################################################################################################
    # Initialize objects' instance numbers
    # def explore_scene(self):
    #     agent_height = self.env.last_event.metadata['agent']['position']['y']
    #     for object_id, point in self.openable_points.items():
    #         action = {'action': 'TeleportFull',
    #                   'x': point[0],
    #                   'y': agent_height,
    #                   'z': point[1],
    #                   'rotateOnTeleport': False,
    #                   'rotation': point[2],
    #                   'horizon': point[3]}
    #         event = self.env.step(action)

    #         if event.metadata['lastActionSuccess']:
    #             self.exploration_frames.append(np.array(self.env.last_event.frame[:,:,::-1]))
    #             instance_segs = np.array(self.env.last_event.instance_segmentation_frame)
    #             color_to_object_id = self.env.last_event.color_to_object_id

    #             # find unique instance segs
    #             color_count = Counter()
    #             for x in range(instance_segs.shape[0]):
    #                 for y in range(instance_segs.shape[1]):
    #                     color = instance_segs[y, x]
    #                     color_count[tuple(color)] += 1

    #             for color, num_pixels in color_count.most_common():
    #                 if color in color_to_object_id:
    #                     object_id = color_to_object_id[color]
    #                     object_type = object_id.split('|')[0]
    #                     if "Basin" in object_id:
    #                         object_type += "Basin"

    #                     if object_type in self.STATIC_RECEPTACLES:
    #                         if object_id not in self.receptacles:
    #                             self.receptacles[object_id] = {
    #                                 'object_id': object_id,
    #                                 'object_type': object_type,
    #                                 'locs': action,
    #                                 'num_pixels': num_pixels,
    #                                 'num_id': "%s %d" % (object_type.lower(), self.get_next_num_id(object_type, self.receptacles)),
    #                                 'closed': True if object_type in constants.OPENABLE_CLASS_LIST else None,
    #                                 'visible_objects': []
    #                             }
    #                         # elif object_id in self.receptacles and num_pixels > self.receptacles[object_id]['num_pixels']:
    #                         #     self.receptacles[object_id]['locs'] = action  # .append(action)
    #                         #     self.receptacles[object_id]['num_pixels'] = num_pixels
                                



    #     # update visible objects where the agent visits receptacles
    #     for recep_id, recep_info in self.receptacles.items():
    #         # action = {'action': 'TeleportFull',
    #         #           'x': point[0],
    #         #           'y': agent_height,
    #         #           'z': point[1],
    #         #           'rotateOnTeleport': False,
    #         #           'rotation': point[2],
    #         #           'horizon': point[3]}
    #         action = recep_info['locs']
    #         event = self.env.step(action)

    #         if event.metadata['lastActionSuccess']:
    #             inst_color_count, inst_color_to_object_id = self.get_instance_seg()
    #             recep_object_id = recep_id


    #             # for each unique seg add to object dictionary if it's more visible than before
    #             visible_objects = []
    #             for color, num_pixels in inst_color_count.most_common():
    #                 if color in inst_color_to_object_id:
    #                     object_id = inst_color_to_object_id[color]
    #                     object_type = object_id.split("|")[0]
    #                     object_metadata = self.get_obj_id_from_metadata(object_id)
    #                     is_obj_in_recep = (object_metadata and object_metadata['parentReceptacles'] and len(object_metadata['parentReceptacles']) > 0 and recep_object_id in object_metadata['parentReceptacles'])
    #                     if object_type in self.OBJECTS and object_metadata and (not self.use_gt_relations or is_obj_in_recep):
    #                         if object_id not in self.objects:
    #                             self.objects[object_id] = {
    #                                 'object_id': object_id,
    #                                 'object_type': object_type,
    #                                 'parent': recep_id,
    #                                 'loc': action,
    #                                 'num_pixels': num_pixels,
    #                                 'num_id': "%s %d" % (object_type.lower() if "Sliced" not in object_id else "sliced-%s" % object_type.lower(),
    #                                                     self.get_next_num_id(object_type, self.objects))
    #                             }
    #                         # elif object_id in self.objects and num_pixels > self.objects[object_id]['num_pixels']:
    #                         #     self.objects[object_id]['loc'] = action
    #                         #     self.objects[object_id]['num_pixels'] = num_pixels
    #                         try:
                                
    #                             num_id = self.objects[object_id]['num_id']
    #                             self.receptacles[recep_id]['visible_objects'].append(num_id)
    #                             # self.receptacles[recep_id]['visible_objects'].append(object_id)
    #                         except: pass

    #     for recep_id in self.receptacles.keys():
    #         self.receptacles[recep_id]['objects_inside'] = []
    #         for i in event.metadata['objects']:
    #             if recep_id == i['objectId']:
    #                 object_ids = i.get('receptacleObjectIds', [])
    #                 if object_ids == None: object_ids = []
    #                 for object_id in object_ids:
    #                     if object_id in self.objects:
    #                         self.receptacles[recep_id]['objects_inside'].append(self.objects[object_id]['num_id'])
    #                     else:
    #                         object_type = object_id.split('|')[0]
    #                         self.receptacles[recep_id]['objects_inside'].append("%s %d" % (object_type.lower() if "Sliced" not in object_id else "sliced-%s" % object_type.lower(),
    #                                                     self.get_next_num_id(object_type, self.objects)))
                    
        



    #     map = dict()
    #     for key, value in self.receptacles.items():
    #         num_id = value['num_id']
    #         map[num_id] = value
    #     self.receptacles_instance_id = map
        
    #     ## only to save
    #     self.save_receps()

    def add_visible_objects(self, recep_id, action):
        # objects
        inst_color_count, inst_color_to_object_id = self.get_instance_seg()
        
        # for each unique seg add to object dictionary if it's more visible than before
        for color, num_pixels in inst_color_count.most_common():
            if color in inst_color_to_object_id:
                object_id = inst_color_to_object_id[color]
                object_type = object_id.split("|")[0]
                object_metadata = self.get_obj_id_from_metadata(object_id)
                is_obj_in_recep = (object_metadata and object_metadata['parentReceptacles'] and len(object_metadata['parentReceptacles']) > 0 and recep_id in object_metadata['parentReceptacles'])
                if object_type in self.OBJECTS and object_metadata and (not self.use_gt_relations or is_obj_in_recep):
                    if object_id not in self.objects:
                        self.objects[object_id] = {
                            'object_id': object_id,
                            'object_type': object_type,
                            'parent': recep_id,
                            'loc': action,
                            'num_pixels': num_pixels,
                            'num_id': "%s %d" % (object_type.lower() if "Sliced" not in object_id else "sliced-%s" % object_type.lower(),
                                                self.get_next_num_id(object_type, self.objects))
                        }
                    try:
                        num_id = self.objects[object_id]['num_id']
                        self.receptacles[recep_id]['visible_objects'].append(num_id)
                    except: pass

    # Initialize objects' instance numbers
    def explore_scene(self):
        agent_height = self.env.last_event.metadata['agent']['position']['y']
        for recep_id, point in self.openable_points.items():
            action = {'action': 'TeleportFull',
                      'x': point[0],
                      'y': agent_height,
                      'z': point[1],
                      'rotateOnTeleport': False,
                      'rotation': point[2],
                      'horizon': point[3]}
            event = self.env.step(action)

            if event.metadata['lastActionSuccess']:
                self.exploration_frames.append(np.array(self.env.last_event.frame[:,:,::-1]))
                instance_segs = np.array(self.env.last_event.instance_segmentation_frame)
                color_to_object_id = self.env.last_event.color_to_object_id

                # find unique instance segs
                color_count = Counter()
                for x in range(instance_segs.shape[0]):
                    for y in range(instance_segs.shape[1]):
                        color = instance_segs[y, x]
                        color_count[tuple(color)] += 1

                for color, num_pixels in color_count.most_common():
                    if color in color_to_object_id:
                        obj_id = color_to_object_id[color]
                        object_type = obj_id.split('|')[0]
                        if "Basin" in obj_id:
                            object_type += "Basin"
                        if object_type in self.STATIC_RECEPTACLES:
                            if obj_id in self.openable_points:
                                if recep_id == obj_id:
                                    self.receptacles[obj_id] = {
                                        'object_id': obj_id,
                                        'object_type': object_type,
                                        'locs': action,
                                        'num_pixels': num_pixels,
                                        'num_id': "%s %d" % (object_type.lower(), self.get_next_num_id(object_type, self.receptacles)),
                                        'closed': True if object_type in constants.OPENABLE_CLASS_LIST else None,
                                        'visible_objects': []
                                    }
                                    
                                    # self.add_visible_objects(recep_id, action)

                                    for color, num_pixels in color_count.most_common():
                                        if color in color_to_object_id:
                                            object_id = color_to_object_id[color]
                                            object_type = object_id.split("|")[0]
                                            object_metadata = self.get_obj_id_from_metadata(object_id)
                                            is_obj_in_recep = (object_metadata and object_metadata['parentReceptacles'] and len(object_metadata['parentReceptacles']) > 0 and recep_id in object_metadata['parentReceptacles'])
                                            if object_type in self.OBJECTS and object_metadata and (not self.use_gt_relations or is_obj_in_recep):
                                                if object_id not in self.objects:
                                                    self.objects[object_id] = {
                                                        'object_id': object_id,
                                                        'object_type': object_type,
                                                        'parent': recep_id,
                                                        'loc': action,
                                                        'num_pixels': num_pixels,
                                                        'num_id': "%s %d" % (object_type.lower() if "Sliced" not in object_id else "sliced-%s" % object_type.lower(),
                                                                            self.get_next_num_id(object_type, self.objects))
                                                    }
                                                try:
                                                    num_id = self.objects[object_id]['num_id']
                                                    self.receptacles[recep_id]['visible_objects'].append(num_id)
                                                except: pass



                            else: # for receptacle not in openable points (e.g., CoffeeMachine, Toaster)
                                if obj_id not in self.receptacles:
                                    self.receptacles[obj_id] = {
                                        'object_id': obj_id,
                                        'object_type': object_type,
                                        'locs': action,
                                        'num_pixels': num_pixels,
                                        'num_id': "%s %d" % (object_type.lower(), self.get_next_num_id(object_type, self.receptacles)),
                                        'closed': True if object_type in constants.OPENABLE_CLASS_LIST else None,
                                        'visible_objects': []
                                    }
                                elif obj_id in self.receptacles and num_pixels > self.receptacles[obj_id]['num_pixels']:
                                    self.receptacles[obj_id]['locs'] = action
                                    self.receptacles[obj_id]['num_pixels'] = num_pixels
                                    
        # update visible objects where the agent visits receptacles
        for recep_id, recep_info in self.receptacles.items():
            if recep_id in self.openable_points:
                continue
            action = recep_info['locs']
            event = self.env.step(action)

            if event.metadata['lastActionSuccess']:
                self.add_visible_objects(recep_id, action)

        map = dict()
        for key, value in self.receptacles.items():
            num_id = value['num_id']
            map[num_id] = value
        self.receptacles_instance_id = map
        
        ## only to save
        # self.save_receps()


    def update_visible_objects(self, recep_instance):
        self.exploration_frames.append(np.array(self.env.last_event.frame[:,:,::-1]))
        inst_color_count, inst_color_to_object_id = self.get_instance_seg()
        
        recep_id = self.receptacles_instance_id[recep_instance]

        # for each unique seg add to object dictionary if it's more visible than before
        visible_objects = []
        for color, num_pixels in inst_color_count.most_common():
            if color in inst_color_to_object_id:
                object_id = inst_color_to_object_id[color]
                object_type = object_id.split("|")[0]
                object_metadata = self.get_obj_id_from_metadata(object_id)
                is_obj_in_recep = (object_metadata and object_metadata['parentReceptacles'] and len(object_metadata['parentReceptacles']) > 0 and recep_id in object_metadata['parentReceptacles'])
                if object_type in self.OBJECTS and object_metadata and (not self.use_gt_relations or is_obj_in_recep):
                    if self.objects[object_id]['num_id'] not in self.inventory:
                        try:
                            num_id = self.objects[object_id]['num_id']
                            visible_objects.append(num_id)
                            # self.receptacles[recep_id]['visible_objects'].append(num_id)
                            # self.receptacles[recep_id]['visible_objects'].append(object_id)
                        except: pass

        return visible_objects
    
    def update_visible_objects_all(self):
        for recep_id, data in self.receptacles.items():
            action = self.receptacles[recep_id]['locs']
            event = self.env.step(action)

            if event.metadata['lastActionSuccess']:
                self.exploration_frames.append(np.array(self.env.last_event.frame[:,:,::-1]))
                instance_segs = np.array(self.env.last_event.instance_segmentation_frame)
                color_to_object_id = self.env.last_event.color_to_object_id

                # find unique instance segs
                color_count = Counter()
                for x in range(instance_segs.shape[0]):
                    for y in range(instance_segs.shape[1]):
                        color = instance_segs[y, x]
                        color_count[tuple(color)] += 1
                
                self.receptacles[recep_id]['visible_objects'] = []
                
                for color, num_pixels in color_count.most_common():
                    if color in color_to_object_id:
                        object_id = color_to_object_id[color]
                        object_type = object_id.split("|")[0]
                        object_metadata = self.get_obj_id_from_metadata(object_id)
                        is_obj_in_recep = (object_metadata and object_metadata['parentReceptacles'] and len(object_metadata['parentReceptacles']) > 0 and recep_id in object_metadata['parentReceptacles'])
                        if object_type in self.OBJECTS and object_metadata and (not self.use_gt_relations or is_obj_in_recep):
                            try:
                                num_id = self.objects[object_id]['num_id']
                                self.receptacles[recep_id]['visible_objects'].append(num_id)
                            except: pass

        map = dict()
        for key, value in self.receptacles.items():
            num_id = value['num_id']
            map[num_id] = value
        self.receptacles_instance_id = map
        self.env.step(self.receptacles_instance_id[self.curr_recep]['locs'])
    
    # ground-truth instance segemetations (with consistent object IDs) from THOR
    def get_instance_seg(self):
        instance_segs = np.array(self.env.last_event.instance_segmentation_frame)
        inst_color_to_object_id = self.env.last_event.color_to_object_id

        # find unique instance segs
        inst_color_count = Counter()
        for x in range(instance_segs.shape[0]):
            for y in range(instance_segs.shape[1]):
                color = instance_segs[y, x]
                inst_color_count[tuple(color)] += 1
        return inst_color_count, inst_color_to_object_id

    # ground-truth object state info maintained by ThorEnv
    def get_object_state(self, object_id):
        is_clean = object_id in self.env.cleaned_objects
        is_hot = object_id in self.env.heated_objects
        is_cool = object_id in self.env.cooled_objects
        is_sliced = 'Sliced' in object_id
        return is_clean, is_cool, is_hot, is_sliced

    def get_admissible_commands(self):
        return extract_admissible_commands_with_heuristics(self.intro, self.frame_desc, self.feedback,
                                                           self.curr_recep, self.inventory)

    def print_frame(self, recep, loc):
        inst_color_count, inst_color_to_object_id = self.get_instance_seg()
        recep_object_id = recep['object_id']

        # for each unique seg add to object dictionary if it's more visible than before
        visible_objects = []
        for color, num_pixels in inst_color_count.most_common():
            if color in inst_color_to_object_id:
                object_id = inst_color_to_object_id[color]
                object_type = object_id.split("|")[0]
                object_metadata = self.get_obj_id_from_metadata(object_id)
                is_obj_in_recep = (object_metadata and object_metadata['parentReceptacles'] and len(object_metadata['parentReceptacles']) > 0 and recep_object_id in object_metadata['parentReceptacles'])
                if object_type in self.OBJECTS and object_metadata and (not self.use_gt_relations or is_obj_in_recep):
                    if object_id not in self.objects:
                        self.objects[object_id] = {
                            'object_id': object_id,
                            'object_type': object_type,
                            'parent': recep['object_id'],
                            'loc': loc,
                            'num_pixels': num_pixels,
                            'num_id': "%s %d" % (object_type.lower() if "Sliced" not in object_id else "sliced-%s" % object_type.lower(),
                                                 self.get_next_num_id(object_type, self.objects))
                        }
                    elif object_id in self.objects and num_pixels > self.objects[object_id]['num_pixels']:
                        self.objects[object_id]['loc'] = loc
                        self.objects[object_id]['num_pixels'] = num_pixels

                    if self.objects[object_id]['num_id'] not in self.inventory:
                        visible_objects.append(self.objects[object_id]['num_id'])

        visible_objects_with_articles = ["a %s," % vo for vo in visible_objects]
        feedback = ""
        if len(visible_objects) > 0:
            feedback = "On the %s, you see %s" % (recep['num_id'], self.fix_and_comma_in_the_end(' '.join(visible_objects_with_articles)))
        elif not recep['closed'] and len(visible_objects) == 0:
            feedback = "On the %s, you see nothing." % (recep['num_id'])

        return visible_objects, feedback

    def step(self, action_str):
        event = None
        self.feedback = "Nothing happens.\n"

        try:
            cmd = self.parse_command(action_str)

            if cmd['action'] == self.Action.GOTO:
                target = cmd['tar']
                recep = self.get_object(target, self.receptacles)
                if recep and recep['num_id'] == self.curr_recep:
                    self.feedback = "You are already at " + action_str.split("go to ")[-1] + ".\n"
                    state_feedback = "The {} is {}. ".format(self.curr_recep, "closed" if recep['closed'] else "open") if recep['closed'] is not None else ""
                    self.visible_objects, feedback = self.print_frame(recep, self.curr_loc)
                    self.feedback += state_feedback + feedback
                    
                else:
                    self.curr_loc = recep['locs']
                    try:
                        if recep['locs'] != self.receptacles_instance_id[self.curr_recep]['locs']:
                            event = self.navigate(self.curr_loc)
                    except:
                        event = self.navigate(self.curr_loc)
                    self.curr_recep = recep['num_id']
                    self.visible_objects, self.feedback = self.print_frame(recep, self.curr_loc)

                    # feedback conditions
                    loc_id = list(self.receptacles.keys()).index(recep['object_id'])
                    loc_feedback = "You arrive at loc %s. " % loc_id
                    state_feedback = "The {} is {}. ".format(self.curr_recep, "closed" if recep['closed'] else "open") if recep['closed'] is not None else ""
                    loc_state_feedback = loc_feedback + state_feedback
                    # self.feedback = loc_state_feedback + self.feedback if "closed" not in state_feedback else loc_state_feedback
                    self.feedback = loc_state_feedback + self.feedback
                    self.frame_desc = str(self.feedback)
            
            # if cmd['action'] == self.Action.GOTO:
            #     target = cmd['tar']
            #     recep = self.get_object(target, self.receptacles)
            #     if recep and recep['num_id'] == self.curr_recep:
            #         return self.feedback
            #     self.curr_loc = recep['locs']
            #     event = self.navigate(self.curr_loc)
            #     self.curr_recep = recep['num_id']
            #     self.visible_objects, self.feedback = self.print_frame(recep, self.curr_loc)

            #     # feedback conditions
            #     loc_id = list(self.receptacles.keys()).index(recep['object_id'])
            #     loc_feedback = "You arrive at loc %s. " % loc_id
            #     state_feedback = "The {} is {}. ".format(self.curr_recep, "closed" if recep['closed'] else "open") if recep['closed'] is not None else ""
            #     loc_state_feedback = loc_feedback + state_feedback
            #     self.feedback = loc_state_feedback + self.feedback if "closed" not in state_feedback else loc_state_feedback
            #     self.frame_desc = str(self.feedback)

            elif cmd['action'] == self.Action.PICK:
                obj, rel, tar = cmd['obj'], cmd['rel'], cmd['tar']
                if obj in self.visible_objects:
                    object = self.get_object(obj, self.objects)
                    event = self.env.step({'action': "PickupObject",
                                           'objectId': object['object_id'],
                                           'forceAction': True})

                    if event.metadata['lastActionSuccess']:
                        self.inventory.append(object['num_id'])
                        self.feedback = "You pick up the %s from the %s." % (obj, tar)

            elif cmd['action'] == self.Action.PUT:
                obj, rel, tar = cmd['obj'], cmd['rel'], cmd['tar']
                recep = self.get_object(tar, self.receptacles)
                event = self.env.step({'action': "PutObject",
                                       'objectId': self.env.last_event.metadata['inventoryObjects'][0]['objectId'],
                                       'receptacleObjectId': recep['object_id'],
                                       'forceAction': True})
                if event.metadata['lastActionSuccess']:
                    self.inventory.pop()
                    self.feedback = "You put the %s %s the %s." % (obj, rel, tar)
                self.visible_objects, _ = self.print_frame(recep, self.curr_loc)

            elif cmd['action'] == self.Action.OPEN:
                target = cmd['tar']
                recep = self.get_object(target, self.receptacles)
                event = self.env.step({'action': "OpenObject",
                                       'objectId': recep['object_id'],
                                       'forceAction': True})
                self.receptacles[recep['object_id']]['closed'] = False
                self.visible_objects, self.feedback = self.print_frame(recep, self.curr_loc)
                action_feedback = "You open the %s. The %s is open. " % (target, target)
                self.feedback = action_feedback + self.feedback.replace("On the %s" % target, "In it")
                self.frame_desc = str(self.feedback)

            elif cmd['action'] == self.Action.CLOSE:
                target = cmd['tar']
                recep = self.get_object(target, self.receptacles)
                event = self.env.step({'action': "CloseObject",
                                       'objectId': recep['object_id'],
                                       'forceAction': True})
                self.receptacles[recep['object_id']]['closed'] = True
                self.feedback = "You close the %s." % target

            elif cmd['action'] == self.Action.TOGGLE:
                target = cmd['tar']
                obj = self.get_object(target, self.objects)
                event = self.env.step({'action': "ToggleObjectOn",
                                       'objectId': obj['object_id'],
                                       'forceAction': True})
                self.feedback = "You turn on the %s." % target

            elif cmd['action'] == self.Action.HEAT:
                obj, rel, tar = cmd['obj'], cmd['rel'], cmd['tar']
                obj_id = self.env.last_event.metadata['inventoryObjects'][0]['objectId']
                recep = self.get_object(tar, self.receptacles)

                # open the microwave, heat the object, take the object, close the microwave
                events = []
                events.append(self.env.step({'action': 'OpenObject', 'objectId': recep['object_id'], 'forceAction': True}))
                events.append(self.env.step({'action': 'PutObject', 'objectId': obj_id, 'receptacleObjectId': recep['object_id'], 'forceAction': True}))
                events.append(self.env.step({'action': 'CloseObject', 'objectId': recep['object_id'], 'forceAction': True}))
                events.append(self.env.step({'action': 'ToggleObjectOn', 'objectId': recep['object_id'], 'forceAction': True}))
                events.append(self.env.step({'action': 'Pass'}))
                events.append(self.env.step({'action': 'ToggleObjectOff', 'objectId': recep['object_id'], 'forceAction': True}))
                events.append(self.env.step({'action': 'OpenObject', 'objectId': recep['object_id'], 'forceAction': True}))
                events.append(self.env.step({'action': 'PickupObject', 'objectId': obj_id, 'forceAction': True}))
                events.append(self.env.step({'action': 'CloseObject', 'objectId': recep['object_id'], 'forceAction': True}))

                if all(e.metadata['lastActionSuccess'] for e in events) and self.curr_recep == tar:
                    self.feedback = "You heat the %s using the %s." % (obj, tar)

            elif cmd['action'] == self.Action.CLEAN:
                obj, rel, tar = cmd['obj'], cmd['rel'], cmd['tar']
                object = self.env.last_event.metadata['inventoryObjects'][0]
                sink = self.get_obj_cls_from_metadata('BathtubBasin' if "bathtubbasin" in tar else "SinkBasin")
                faucet = self.get_obj_cls_from_metadata('Faucet')

                # put the object in the sink, turn on the faucet, turn off the faucet, pickup the object
                events = []
                events.append(self.env.step({'action': 'PutObject', 'objectId': object['objectId'], 'receptacleObjectId': sink['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'ToggleObjectOn', 'objectId': faucet['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'Pass'}))
                events.append(self.env.step({'action': 'ToggleObjectOff', 'objectId': faucet['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'PickupObject', 'objectId': object['objectId'], 'forceAction': True}))

                if all(e.metadata['lastActionSuccess'] for e in events) and self.curr_recep == tar:
                    self.feedback = "You clean the %s using the %s." % (obj, tar)

            elif cmd['action'] == self.Action.COOL:
                obj, rel, tar = cmd['obj'], cmd['rel'], cmd['tar']
                object = self.env.last_event.metadata['inventoryObjects'][0]
                fridge = self.get_obj_cls_from_metadata('Fridge')

                # open the fridge, put the object inside, close the fridge, open the fridge, pickup the object
                events = []
                events.append(self.env.step({'action': 'OpenObject', 'objectId': fridge['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'PutObject', 'objectId': object['objectId'], 'receptacleObjectId': fridge['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'CloseObject', 'objectId': fridge['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'Pass'}))
                events.append(self.env.step({'action': 'OpenObject', 'objectId': fridge['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'PickupObject', 'objectId': object['objectId'], 'forceAction': True}))
                events.append(self.env.step({'action': 'CloseObject', 'objectId': fridge['objectId'], 'forceAction': True}))

                if all(e.metadata['lastActionSuccess'] for e in events) and self.curr_recep == tar:
                    self.feedback = "You cool the %s using the %s." % (obj, tar)

            elif cmd['action'] == self.Action.SLICE:
                obj, rel, tar = cmd['obj'], cmd['rel'], cmd['tar']
                object = self.get_object(obj, self.objects)
                inventory_objects = self.env.last_event.metadata['inventoryObjects']
                if 'Knife' in inventory_objects[0]['objectType']:
                    event = self.env.step({'action': "SliceObject",
                                           'objectId': object['object_id']})
                self.feedback = "You slice %s with the %s" % (obj, tar)
                self.visible_objects, _ = self.print_frame(recep, self.curr_loc)

            elif cmd['action'] == self.Action.INVENTORY:
                if len(self.inventory) > 0:
                    self.feedback = "You are carrying: a %s" % (self.inventory[0])
                else:
                    self.feedback = "You are not carrying anything."

            elif cmd['action'] == self.Action.EXAMINE:
                target = cmd['tar']
                receptacle = self.get_object(target, self.receptacles)
                object = self.get_object(target, self.objects)

                if receptacle:
                    self.visible_objects, self.feedback = self.print_frame(receptacle, self.curr_loc)
                    self.frame_desc = str(self.feedback)
                elif object:
                    self.feedback = self.print_object(object)

            elif cmd['action'] == self.Action.LOOK:
                if self.curr_recep == "nothing":
                    self.feedback = "You are in the middle of a room. Looking quickly around you, you see nothing."
                else:
                    self.feedback = "You are facing the %s. Next to it, you see nothing." % self.curr_recep

            ### Add Toggle On/Off actions ###
            elif cmd['action'] == self.Action.TOGGLEON:
                target = cmd['tar']
                target_name = self.extract_text(target)
                target_dict = {'faucet': 'Faucet',
                               'microwave': 'Microwave',
                               'coffeemachine': 'CoffeeMachine',
                               'stoveburner': 'Stoveburner',
                               'stoveknob': 'Stoveknob',
                               'desklamp': 'DeskLamp',
                               'floorlamp': 'FloorLamp'}
                target_object = self.get_obj_cls_from_metadata(target_dict[target_name])
                # recep = self.get_object(target, self.receptacles)
                event = self.env.step({'action': "ToggleObjectOn",
                                       'objectId': target_object['objectId'],
                                       'forceAction': True})
                self.feedback = "You turn on the %s." % target

            elif cmd['action'] == self.Action.TOGGLEOFF:
                target = cmd['tar']
                target_name = self.extract_text(target)
                target_dict = {'faucet': 'Faucet',
                               'microwave': 'Microwave',
                               'coffeemachine': 'CoffeeMachine',
                               'stoveburner': 'Stoveburner',
                               'stoveknob': 'Stoveknob',
                               'desklamp': 'DeskLamp',
                               'floorlamp': 'FloorLamp'}
                target_object = self.get_obj_cls_from_metadata(target_dict[target_name])
                # recep = self.get_object(target, self.receptacles)
                event = self.env.step({'action': "ToggleObjectOff",
                                       'objectId': target_object['objectId'],
                                       'forceAction': True})
                self.feedback = "You turn off the %s." % target
                
            elif cmd['action'] == self.Action.WAIT:
                time = int(cmd['tar'])
                event = self.env.step({'action': 'Pass', 'time': time})
                self.feedback = "You wait for " + str(time) + " time steps."

        except:
            if self.debug:
                print(traceback.format_exc())

        if event and not event.metadata['lastActionSuccess']:
            self.feedback = "Nothing happens."
            if self.debug:
                print(event.metadata['errorMessage'])

        # add information of time step to self.feedback
        self.feedback += "\nThe time steps taken so far are " + str(self.env.steps_taken) + ".\n"

        if self.debug:
            print(self.feedback)
        return self.feedback

