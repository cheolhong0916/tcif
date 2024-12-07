import os
import sys
import json
import re
import copy
import random
import alfworld.gen.constants as constants
from alfworld.gen.utils.image_util import compress_mask, decompress_mask
from alfworld.agents.utils.misc import get_templated_task_desc, get_human_anns_task_desc, NumpyArrayEncoder
from enum import Enum

class BaseAgent(object):
    '''
    Base class for controllers
    '''

    # constants
    RECEPTACLES = set(constants.RECEPTACLES) | {'Sink', 'Bathtub'}
    OBJECTS = (set(constants.OBJECTS_WSLICED) - set(RECEPTACLES)) | set(constants.MOVABLE_RECEPTACLES)
    OBJECTS -= {'Blinds', 'Boots', 'Cart', 'Chair', 'Curtains', 'Footstool', 'Mirror', 'LightSwtich', 'Painting', 'Poster', 'ShowerGlass', 'Window'}
    STATIC_RECEPTACLES = set(RECEPTACLES) - set(constants.MOVABLE_RECEPTACLES)

    # action enum
    class Action(Enum):
        PASS = 0,
        GOTO = 1,
        PICK = 2,
        PUT = 3,
        OPEN = 4,
        CLOSE = 5,
        TOGGLE = 6,
        HEAT = 7,
        CLEAN = 8,
        COOL = 9,
        SLICE = 10,
        INVENTORY = 11,
        EXAMINE = 12,
        LOOK = 13,
        TOGGLEON = 14,
        TOGGLEOFF = 15,
        WAIT = 16

    def __init__(self, env, traj_data, traj_root,
                 load_receps=False, debug=False,
                 goal_desc_human_anns_prob=0.0,
                 recep_filename='objects_information.json', exhaustive_exploration=False):
        self.env = env
        self.traj_data = traj_data
        self.debug = debug
        self.traj_root = traj_root
        self.load_receps = load_receps
        self.recep_file = os.path.join(traj_root, recep_filename)
        self.objects = {}
        self.receptacles = {}
        self.visible_objects = []
        self.exhaustive_exploration = exhaustive_exploration
        self.goal_desc_human_anns_prob = goal_desc_human_anns_prob

        self.feedback = ""
        self.curr_loc = {'action': "Pass"}
        self.curr_recep = "nothing"
        self.inventory = []
        self.intro = ""
        self.frame_desc = ""

        self.init_scene(load_receps)
        self.setup_navigator()
        self.print_intro()

    # explore the scene to build receptacle map
    def init_scene(self, load_receps):
        if load_receps and os.path.isfile(self.recep_file):
            with open(self.recep_file, 'r') as f:
                self.receptacles = json.load(f)
            for recep_id, recep in self.receptacles.items():
                if 'mask' in recep:
                    recep['mask'] = decompress_mask(recep['mask'])
        else:
            self.receptacles = {}
            if self.exhaustive_exploration:
                self.explore_scene_exhaustively()
            else:
                try:
                    with open(self.recep_file) as f:
                        data = json.load(f)
                    self.receptacles = data['receptacles']
                    self.receptacles_instance_id = data['receptacles_instance_id']
                    self.objects = data['objects']
                except:
                    self.explore_scene()

    def get_object(self, name, obj_dict):
        for id, obj in obj_dict.items():
            if obj['num_id'] == name:
                return obj
        return None

    def get_next_num_id(self, object_type, obj_dict):
        return len([obj for _, obj in obj_dict.items() if obj['object_type'] == object_type]) + 1

    def fix_and_comma_in_the_end(self, desc):
        sc = desc.split(",")
        if len(sc) > 2:
            return ",".join(sc[:-2]) + ", and%s." % sc[-2]
        elif len(sc) == 2:
            return desc.rstrip(",") + "."
        else:
            return desc

    def explore_scene(self):
        raise NotImplementedError()

    def explore_scene_exhaustively(self):
        raise NotImplementedError()

    def get_admissible_commands(self):
        raise NotImplementedError()

    def get_instance_seg(self):
        raise NotImplementedError()

    def get_object_state(self, object_id):
        raise NotImplementedError()

    # dump receptacle map to disk
    # def save_receps(self):
    #     receptacles = copy.deepcopy(self.receptacles)
    #     for recep_id, recep in receptacles.items():
    #         if 'mask' in recep:
    #             recep['mask'] = compress_mask(recep['mask'])
    #     with open(self.recep_file, 'w') as f:
    #         json.dump(receptacles, f, indent=4) #, cls=NumpyArrayEncoder)

    def save_receps(self):
        # if not os.path.exists(self.recep_file):
            data = dict()
            data['receptacles'] = copy.deepcopy(self.receptacles)
            data['receptacles_instance_id'] = copy.deepcopy(self.receptacles_instance_id)
            data['objects'] = copy.deepcopy(self.objects)
            with open(self.recep_file, 'w') as f:
                json.dump(data, f, indent=4) #, cls=NumpyArrayEncoder)

    ##########################################################
    # def desired_state_check(self,td):

    ##########################################################


    # display initial observation and task text
    def print_intro(self):
        self.feedback = "-= Welcome to TextWorld, ALFRED! =-\n\nYou are in the middle of a room. Looking quickly around you, you see "
        recep_list = ["a %s," % (recep['num_id']) for id, recep in self.receptacles.items()]
        self.feedback += self.fix_and_comma_in_the_end(" ".join(recep_list)) + "\n\n"

        # self.feedback += "The time steps taken so far are " + str(self.env.steps_taken) + ".\n"

        self.feedback += "Your task is to:\n"
        task_num = 1
        for idx, td in enumerate(self.traj_data):
            # self.feedback += str(task_num) + ". "
            self.feedback += '"'
            # if random.random() < self.goal_desc_human_anns_prob:
            #     task = get_human_anns_task_desc(td)
            # else:
            #     task = get_templated_task_desc(td)
            task = td['turk_annotations']['anns'][0]['task_desc']
            self.feedback += task
            if td['task_type'] == 'pick_heat_then_place_in_recep':
                self.feedback += ' The ' + td['pddl_params']['object_target'].lower() + ' should be ' + td['desired_state']['heat'] + '. '
                if td['desired_state']['heat'] == 'warm':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['heat'] + \
                                    ', you should cook it with the microwave more than ' + str(constants.TIME_THRESHOLDS['WARM']) + ' time steps.'
                elif td['desired_state']['heat'] == 'hot':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['heat'] + \
                                    ', you should cook it with the microwave more than ' + str(constants.TIME_THRESHOLDS['HOT']) + ' time steps.'
                elif td['desired_state']['heat'] == 'boiling':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['heat'] + \
                                    ', you should cook it with the microwave more than ' + str(constants.TIME_THRESHOLDS['BOILING']) + ' time steps.'

            if td['task_type'] == 'pick_cool_then_place_in_recep':
                self.feedback += ' The ' + td['pddl_params']['object_target'].lower() + ' should be ' + td['desired_state']['cool'] + '. '
                if td['desired_state']['cool'] == 'cool':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['cool'] + \
                                    ', you should rest it in the fridge more than ' + str(constants.TIME_THRESHOLDS['COOL']) + ' time steps.'
                elif td['desired_state']['cool'] == 'cold':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['cool'] + \
                                    ', you should rest it in the fridge more than ' + str(constants.TIME_THRESHOLDS['COLD']) + ' time steps.'
                elif td['desired_state']['cool'] == 'freezing':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['cool'] + \
                                    ', you should rest it in the fridge more than ' + str(constants.TIME_THRESHOLDS['FREEZING']) + ' time steps.'

            if td['task_type'] == 'pick_clean_then_place_in_recep':
                self.feedback += ' The ' + td['pddl_params']['object_target'].lower() + ' should be ' + td['desired_state']['clean'] + '. '
                if td['desired_state']['clean'] == 'rinsed':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['clean'] + \
                                    ', you should put it in the sinkbasin, toggle on the faucet, and wait for it to be ' + \
                                    td['desired_state']['clean'] + ' more than ' + str(constants.TIME_THRESHOLDS['RINSED']) + ' time steps.'
                elif td['desired_state']['clean'] == 'washed':
                    self.feedback += 'To make ' + td['pddl_params']['object_target'].lower() + \
                                    (' slice' if td['pddl_params']['object_sliced'] else '') + \
                                    ' be ' + td['desired_state']['clean'] + \
                                    ', you should put it in the sinkbasin, toggle on the faucet, and wait for it to be ' + \
                                    td['desired_state']['clean'] + ' more than ' + str(constants.TIME_THRESHOLDS['WASHED']) + ' time steps.'

            if idx == len(self.traj_data)-1:
                self.feedback += '"\n'
            else:
                self.feedback += '",\n'

        # self.feedback += "Your task is to: %s" % task
        self.env.steps_taken = 0
        self.feedback += "\nNow you start from time step 0.\n"
        self.intro = str(self.feedback)

    # choose between different navigator available
    def setup_navigator(self):
        self.navigator = self.env  # by default, directly teleport with THOR API

    def print_frame(self, recep, loc):
        raise NotImplementedError()

    # display properties of an object
    def print_object(self, object):
        object_id, object_name = object['object_id'], object['num_id']

        is_clean, is_cool, is_hot, is_sliced = self.get_object_state(object_id)

        # by default, nothing interesting about the object
        feedback = "This is a normal %s" % object_name

        sliced_str = "sliced " if is_sliced else ""
        if is_hot and is_cool and is_clean:
            feedback = "This is a hot/cold and clean %s%s." % (sliced_str, object_name)  # TODO: weird?
        elif is_hot and is_clean:
            feedback = "This is a hot and clean %s%s." % (sliced_str, object_name)
        elif is_cool and is_clean:
            feedback = "This is a cool and clean %s%s." % (sliced_str, object_name)
        elif is_hot and is_cool:
            feedback = "This is a hot/cold %s%s." % (sliced_str, object_name)
        elif is_clean:
            feedback = "This is a clean %s%s." % (sliced_str, object_name)
        elif is_hot:
            feedback = "This is a hot %s%s." % (sliced_str, object_name)
        elif is_cool:
            feedback = "This is a cool %s%s." % (sliced_str, object_name)

        return feedback

    # command parser
    def parse_command(self, action_str):

        def get_triplet(astr, key):
            astr = astr.replace(key, "").split()
            obj, rel, tar = ' '.join(astr[:2]), astr[2], ' '.join(astr[-2:])
            return obj, rel, tar

        action_str = str(action_str).lower().strip()

        if "go to " in action_str:
            tar = action_str.replace("go to ", "")
            return {'action': self.Action.GOTO, 'tar': tar}
        elif "take " in action_str:
            obj, rel, tar = get_triplet(action_str, "take ")
            return {'action': self.Action.PICK, 'obj': obj, 'rel': rel, 'tar': tar}
        elif "put " in action_str:
            obj, rel, tar = get_triplet(action_str, "put ")
            return {'action': self.Action.PUT, 'obj': obj, 'rel': rel, 'tar': tar}
        elif "open " in action_str:
            tar = action_str.replace("open ", "")
            return {'action': self.Action.OPEN, 'tar': tar}
        elif "close " in action_str:
            tar = action_str.replace("close ", "")
            return {'action': self.Action.CLOSE, 'tar': tar}
        elif "use " in action_str:
            tar = action_str.replace("use ", "")
            return {'action': self.Action.TOGGLE, 'tar': tar}
        elif "heat " in action_str:
            obj, rel, tar = get_triplet(action_str, "heat ")
            return {'action': self.Action.HEAT, 'obj': obj, 'rel': rel, 'tar': tar}
        elif "cool " in action_str:
            obj, rel, tar = get_triplet(action_str, "cool ")
            return {'action': self.Action.COOL, 'obj': obj, 'rel': rel, 'tar': tar}
        elif "clean " in action_str:
            obj, rel, tar = get_triplet(action_str, "clean ")
            return {'action': self.Action.CLEAN, 'obj': obj, 'rel': rel, 'tar': tar}
        elif "slice " in action_str:
            obj, rel, tar = get_triplet(action_str, "slice ")
            return {'action': self.Action.SLICE, 'obj': obj, 'rel': rel, 'tar': tar}
        elif "inventory" in action_str:
            return {'action': self.Action.INVENTORY}
        elif "examine " in action_str:
            tar = action_str.replace("examine ", "")
            return {'action': self.Action.EXAMINE, 'tar': tar}
        elif "look" in action_str:
            return {'action': self.Action.LOOK}
        
        ### Add Toggle On/Off actions ###
        elif "toggle on" in action_str:
            tar = action_str.replace("toggle on ", "")
            return {'action': self.Action.TOGGLEON, 'tar': tar}
        elif "toggle off" in action_str:
            tar = action_str.replace("toggle off ", "")
            return {'action': self.Action.TOGGLEOFF, 'tar': tar}
        elif "wait for" in action_str:
            time = action_str.replace("wait for ", "")
            time = time.replace(" time steps", "")
            return {'action': self.Action.WAIT, 'tar': time}
        else:
            return {'action': self.Action.PASS}

    def navigate(self, teleport_loc):
        return self.navigator.step(teleport_loc)

    def step(self, action_str):
        self.feedback = "Nothing happens."
        return self.feedback

    def extract_text(self, input_string):
        result = re.sub(r'\d+', '', input_string).strip()
        return result


