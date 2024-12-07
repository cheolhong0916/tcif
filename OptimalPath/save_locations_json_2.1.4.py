#!/usr/bin/env python

import os
import sys
import json
import glob
import random
import argparse
import shutil
from os.path import join as pjoin
from tqdm import trange

import alfworld.agents
from alfworld.info import ALFWORLD_DATA
from alfworld.env.thor_env import ThorEnv
from alfworld.agents.detector.mrcnn import load_pretrained_model
# from alfworld.agents.controller import OracleAgent, OracleAStarAgent, MaskRCNNAgent, MaskRCNNAStarAgent
from alfworld.agents.controller_new import OracleAgent, OracleAStarAgent, MaskRCNNAgent, MaskRCNNAStarAgent

ALFWORLD_DATA = "/home/cheolhong/ch/alfworld"
prompt_toolkit_available = False
try:
    # For command line history and autocompletion.
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import InMemoryHistory
    prompt_toolkit_available = sys.stdout.isatty()
except ImportError:
    pass

try:
    # For command line history when prompt_toolkit is not available.
    import readline  # noqa: F401
except ImportError:
    pass


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

def copy_files_with_version_change(src_paths, old_version="json_2.1.1", new_version="json_2.1.4"):
    for src in src_paths:
        # Replace old version with new version in destination path
        dest = src.replace(old_version, new_version)

        # Create directories recursively if they don't exist
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        
        # Copy the file from src to dest
        shutil.copy2(src, dest)

def main(args):
    # start THOR
    # env = ThorEnv(save_frames_to_disk=True)
    env = ThorEnv()
    problems = args.problem
    for _ in trange(len(problems)):
        # load traj_data
        traj_data = []
        root = problems.pop(0)
        print(f"Playing '{root}'.")
        # representative_folder = root.split('/')[-1].split('__')[0]
        for i in os.listdir(root):
            if "trial" in i:
                trial = i
                break

        json_file = os.path.join(root, trial, 'traj_data.json')
        with open(json_file, 'r') as f:
            data = json.load(f)
        floorplan_number = int(data['scene']['floor_plan'].split('FloorPlan')[-1])
        if floorplan_number > 30:
            continue
        if data['task_type'] == "pick_and_place_with_movable_recep":
            continue
        traj_data.append(data)

        # setup scene
        setup_scene(env, traj_data, 0, args)

        args.controller = "oracle"
        # choose controller
        if args.controller == "oracle":
            AgentModule = OracleAgent
            agent = AgentModule(env, traj_data, traj_root=root, load_receps=args.load_receps, debug=args.debug)
        elif args.controller == "oracle_astar":
            AgentModule = OracleAStarAgent
            agent = AgentModule(env, traj_data, traj_root=root, load_receps=args.load_receps, debug=args.debug)
        elif args.controller == "mrcnn":
            AgentModule = MaskRCNNAgent
            mask_rcnn = load_pretrained_model(pjoin(ALFWORLD_DATA, "detectors", "mrcnn.pth"))
            agent = AgentModule(env, traj_data, traj_root=root,
                                pretrained_model=mask_rcnn,
                                load_receps=args.load_receps, debug=args.debug)
        elif args.controller == "mrcnn_astar":
            AgentModule = MaskRCNNAStarAgent
            mask_rcnn = load_pretrained_model(pjoin(ALFWORLD_DATA, "detectors", "mrcnn.pth"))
            agent = AgentModule(env, traj_data, traj_root=root,
                                pretrained_model=mask_rcnn,
                                load_receps=args.load_receps, debug=args.debug)
        else:
            raise NotImplementedError()
        
        # src_paths = [json_file, json_file.split('trial')[0]+'receps_objects.json']
        # copy_files_with_version_change(src_paths)


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
        json_path = os.path.join(ALFWORLD_DATA, "json_2.1.4/"+args.split)
        problems = [os.path.join(json_path, item) for item in os.listdir(json_path)]
        args.problem = problems

    if "movable_recep" in args.problem:
        raise ValueError("This problem contains movable receptacles, which is not supported by ALFWorld.")

    main(args)

