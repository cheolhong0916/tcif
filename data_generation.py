import os
from itertools import combinations
import random
import shutil
import json
from tqdm import trange, tqdm

# 랜덤 시드 고정
random.seed(42)

# 원본 및 새 폴더 경로 설정
seen_unseen = "valid_seen"
# seen_unseen = "train"
source_folder_path = "json_3.0.0/" + seen_unseen
destination_folder_base = "json_3.1.0"
destination_folder_path = os.path.join(destination_folder_base, seen_unseen)


#### Generate ####
# # json_3.0.6 폴더와 valid_seen 폴더가 없다면 생성
# os.makedirs(destination_folder_path, exist_ok=True)

# # 폴더 내의 모든 폴더의 JSON 파일을 미리 로드하여 캐시
# def load_json_data(source_folder_path):
#     folder_data = {}
#     for folder in os.listdir(source_folder_path):
#         folder_path = os.path.join(source_folder_path, folder)
#         trial_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
#         trial_data = {}
#         for trial_folder in trial_folders:
#             traj_data_path = os.path.join(folder_path, trial_folder, 'traj_data.json')
#             if os.path.exists(traj_data_path):
#                 with open(traj_data_path, 'r') as f:
#                     traj_data = json.load(f)
#                 trial_data[trial_folder] = traj_data
#         folder_data[folder] = trial_data
#     return folder_data

# # 모든 폴더에 있는 데이터를 미리 로드하여 캐싱
# folder_data_cache = load_json_data(source_folder_path)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}
# for folder in os.listdir(source_folder_path):
#     floorplan_num = folder.split('-')[-1]
#     task_type = folder.split('-')[0]
#     if 'movable' not in task_type and 'Sliced' not in folder:
#         if floorplan_num not in floorplan_dict:
#             floorplan_dict[floorplan_num] = []
#         floorplan_dict[floorplan_num].append((task_type, folder))

# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         for combo in combinations(folders, num_combinations):
#             tasks = [task for task, _ in combo]
#             selected_tasks = {'pick_heat_then_place_in_recep', 'pick_cool_then_place_in_recep', 'pick_clean_then_place_in_recep'}
#             if len(selected_tasks.intersection(tasks)) >= 2:
#                 valid, used_trial_folders = is_valid_combination(combo)
#                 if valid:
#                     valid_combinations.append((combo, used_trial_folders))
#         all_valid_combinations[floorplan] = valid_combinations
#     return all_valid_combinations


# def is_valid_combination(combo):
#     representative_folder_name = combo[0][1]  # 대표 폴더는 첫 번째 폴더
#     representative_traj_data = folder_data_cache[representative_folder_name]
#     used_trial_folders = []  # 사용된 trial 폴더를 저장할 리스트
    
#     # 대표 폴더의 trial 폴더들 중 첫 번째 (정렬된 순서로)
#     representative_trial_folder = sorted(list(representative_traj_data.keys()))[0]
#     used_trial_folders.append(representative_trial_folder)  # 대표 폴더의 첫 trial 폴더 사용

#     representative_object_poses = representative_traj_data[representative_trial_folder]['scene']['object_poses']
#     representative_object_names = [obj['objectName'].split('_')[0] for obj in representative_object_poses]

#     for task_type, folder_name in combo[1:]:
#         trial_data = folder_data_cache[folder_name]
#         # trial 폴더를 정렬하여 첫 번째 폴더 선택
#         trial_folder = sorted(list(trial_data.keys()))[0]
#         used_trial_folders.append(trial_folder)

#         traj_data = trial_data[trial_folder]
#         if traj_data['task_type'] == 'pick_heat_then_place_in_recep':
#             traj_data['desired_state'] = {'heat': random.choice(['warm', 'hot', 'boiling'])}
#         elif traj_data['task_type'] == 'pick_cool_then_place_in_recep':
#             traj_data['desired_state'] = {'cool': random.choice(['cool', 'cold', 'freezing'])}
#         elif traj_data['task_type'] == 'pick_clean_then_place_in_recep':
#             traj_data['desired_state'] = {'clean': random.choice(['rinsed', 'washed'])}

#         object_target = traj_data['pddl_params']['object_target'].split('_')[0]
#         if traj_data['pddl_params']['object_sliced']:
#             return False, used_trial_folders
#         if task_type == 'pick_two_obj_and_place':
#             if representative_object_names.count(object_target) < 2:
#                 return False, used_trial_folders
#         else:
#             if object_target not in representative_object_names:
#                 return False, used_trial_folders

#     return True, used_trial_folders  # valid와 사용된 trial 폴더 리스트 반환

# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
#     return sampled_combinations

# if "valid_seen" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(get_combinations(floorplan_dict, 2), max_count=15)
#     sampled_combinations_3 = sample_combinations(get_combinations(floorplan_dict, 3), max_count=15)
#     # sampled_combinations_4 = sample_combinations(get_combinations(floorplan_dict, 4), max_count=3)
# elif "valid_unseen" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(get_combinations(floorplan_dict, 2), max_count=50)
#     sampled_combinations_3 = sample_combinations(get_combinations(floorplan_dict, 3), max_count=50)
#     # sampled_combinations_4 = sample_combinations(get_combinations(floorplan_dict, 4), max_count=35)
# elif "train" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(get_combinations(floorplan_dict, 2), max_count=100)
#     sampled_combinations_3 = sample_combinations(get_combinations(floorplan_dict, 3), max_count=100)

# def create_combination_folders(combinations_dict, num_combinations):
#     for floorplan, combos in combinations_dict.items():
#         for combo, used_trial_folders in combos:
#             combo_folder_name = f"{num_combinations}_" + "__".join([folder_name for _, folder_name in combo])
#             combo_folder_path = os.path.join(destination_folder_path, combo_folder_name)
#             os.makedirs(combo_folder_path, exist_ok=True)
#             for task_type, folder_name in combo:
#                 for trial_folder in used_trial_folders:
#                     source_trial_path = os.path.join(source_folder_path, folder_name, trial_folder)
#                     dest_trial_path = os.path.join(combo_folder_path, trial_folder)
#                     if os.path.exists(source_trial_path):
#                         shutil.copytree(source_trial_path, dest_trial_path, dirs_exist_ok=True)
#                         try:
#                             with open(dest_trial_path) as f:
#                                 traj_data = json.load(f)
#                             if traj_data['task_type'] == 'pick_heat_then_place_in_recep':
#                                 traj_data['desired_state'] = {'heat': random.choice(['warm', 'hot', 'boiling'])}
#                             elif traj_data['task_type'] == 'pick_cool_then_place_in_recep':
#                                 traj_data['desired_state'] = {'cool': random.choice(['cool', 'cold', 'freezing'])}
#                             elif traj_data['task_type'] == 'pick_clean_then_place_in_recep':
#                                 traj_data['desired_state'] = {'clean': random.choice(['rinsed', 'washed'])}
#                             with open(dest_trial_path, 'w') as f:
#                                 json.dump(traj_data,f,indent=4)
#                         except:
#                             pass
# # def create_combination_folders(combinations_dict, num_combinations, destination_folder_path, source_folder_path):
# #     total_floors = len(combinations_dict)
    
# #     for floorplan_idx in trange(total_floors, desc="Processing Floorplans", leave=True, dynamic_ncols=True):
# #         floorplan = list(combinations_dict.keys())[floorplan_idx]
# #         combos = combinations_dict[floorplan]
        
# #         # 내부 루프 진행 상황 표시
# #         for combo, used_trial_folders in tqdm(combos, desc=f"Processing Combinations for {floorplan}", leave=False, dynamic_ncols=True):
# #             combo_folder_name = f"{num_combinations}_" + "__".join([folder_name for _, folder_name in combo])
# #             combo_folder_path = os.path.join(destination_folder_path, combo_folder_name)
# #             os.makedirs(combo_folder_path, exist_ok=True)

# # 폴더 생성 및 내용물 복사 실행
# create_combination_folders(sampled_combinations_2, 2)
# create_combination_folders(sampled_combinations_3, 3)
# # create_combination_folders(sampled_combinations_4, 4)

# print("폴더 생성이 완료되었습니다.")



###########################################################################################


#############################################################################################################################
#### print configuration ####
import os
from collections import Counter

# 경로 설정
valid_seen_path = destination_folder_path

# 폴더 내의 모든 폴더 이름 가져오기
folders = os.listdir(valid_seen_path)

# Floorplan 번호를 추출하고 고유한 Floorplan 개수 계산
floorplans = set()
for folder_name in folders:
    # '-' 뒤에 있는 마지막 숫자가 Floorplan 번호
    floorplan_num = folder_name.split('-')[-1]
    floorplans.add(floorplan_num)

# 총 Floorplan 개수 출력
print(f"총 사용된 Floorplan 개수: {len(floorplans)}")

# Task 조합 개수 계산
task_types = [
    "pick_and_place_simple",
    "pick_two_obj_and_place",
    "look_at_obj_in_light",
    "pick_clean_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep"
]

# 고유한 task 조합을 담을 집합
task_combinations = set()

# 2개, 3개, 4개 task 조합 개수를 저장할 변수
count_2_tasks = 0
count_3_tasks = 0
count_4_tasks = 0

# 전체 task 조합 개수
total_task_combinations = 0
specific_combinations = {'2tasks':{}, '3tasks':{}}
for folder_name in folders:
    # 폴더 이름에서 task type들을 추출
    tasks = folder_name.split('__')
    
    # task type 카운트와 조합 생성
    # task_combo = tuple(sorted(Counter([task.split('-')[0] for task in tasks if task.split('-')[0] in task_types]).items()))
    task_combo_ = []
    for task in tasks:
        if task.split('-')[0] in task_types:
            task_combo_.append(task.split('-')[0])
        else:
            task_combo_.append(task.split('-')[0][2:])
    task_combo_ = sorted(task_combo_)
    task_combo_str = ""
    for task in task_combo_:
        task_combo_str += task + "/"
    task_combinations.add(tuple(task_combo_))

    # 조합된 task의 개수 세기
    num_tasks = len(tasks)

    # 총 task 조합 개수 업데이트
    total_task_combinations += 1

    # 2개, 3개, 4개의 조합으로 이루어진 task 개수 카운트
    if num_tasks == 2:
        count_2_tasks += 1
        if task_combo_str not in specific_combinations['2tasks']:
            specific_combinations['2tasks'][task_combo_str] = 1
        else:
            specific_combinations['2tasks'][task_combo_str] += 1
    elif num_tasks == 3:
        count_3_tasks += 1
        if task_combo_str not in specific_combinations['3tasks']:
            specific_combinations['3tasks'][task_combo_str] = 1
        else:
            specific_combinations['3tasks'][task_combo_str] += 1
    elif num_tasks == 4:
        count_4_tasks += 1
    
    


# 총 task 조합 개수 출력
print(f"총 task 조합 개수: {len(task_combinations)}")

# 2개, 3개, 4개의 조합으로 이루어진 task 개수 출력
print(f"2개의 조합으로 이루어진 task 개수: {count_2_tasks}")
for key, value in specific_combinations['2tasks'].items():
    print(key, ": ", value)
print(f"3개의 조합으로 이루어진 task 개수: {count_3_tasks}")
for key, value in specific_combinations['3tasks'].items():
    print(key, ": ", value)
print(f"4개의 조합으로 이루어진 task 개수: {count_4_tasks}")

# 총 task 개수 출력
print(f"총 task 개수: {total_task_combinations}")
#############################################################################################################################








# #### train data sampling ####
# import os
# from collections import Counter

# # 경로 설정
# valid_seen_path = destination_folder_path

# # 폴더 내의 모든 폴더 이름 가져오기
# folders = os.listdir(valid_seen_path)

# # Floorplan 번호를 추출하고 고유한 Floorplan 개수 계산
# floorplans = set()
# for folder_name in folders:
#     # '-' 뒤에 있는 마지막 숫자가 Floorplan 번호
#     floorplan_num = folder_name.split('-')[-1]
#     floorplans.add(floorplan_num)

# # 총 Floorplan 개수 출력
# print(f"총 사용된 Floorplan 개수: {len(floorplans)}")

# # Task 조합 개수 계산
# task_types = [
#     "pick_and_place_simple",
#     "pick_two_obj_and_place",
#     "look_at_obj_in_light",
#     "pick_clean_then_place_in_recep",
#     "pick_heat_then_place_in_recep",
#     "pick_cool_then_place_in_recep"
# ]

# # 고유한 task 조합을 담을 집합
# task_combinations = set()

# # 2개, 3개, 4개 task 조합 개수를 저장할 변수
# count_2_tasks = 0
# count_3_tasks = 0

# # 전체 task 조합 개수
# total_task_combinations = 0
# specific_combinations = {'2tasks':{}, '3tasks':{}}
# for folder_name in folders:
#     # 폴더 이름에서 task type들을 추출
#     tasks = folder_name.split('__')
    
#     # task type 카운트와 조합 생성
#     # task_combo = tuple(sorted(Counter([task.split('-')[0] for task in tasks if task.split('-')[0] in task_types]).items()))
#     task_combo_ = []
#     for task in tasks:
#         if task.split('-')[0] in task_types:
#             task_combo_.append(task.split('-')[0])
#         else:
#             task_combo_.append(task.split('-')[0][2:])
#     task_combo_ = sorted(task_combo_)
#     task_combo_str = ""
#     for task in task_combo_:
#         task_combo_str += task + "/"
#     task_combinations.add(tuple(task_combo_))

#     # 조합된 task의 개수 세기
#     num_tasks = len(tasks)

#     # 총 task 조합 개수 업데이트
#     total_task_combinations += 1

#     # 2개, 3개, 4개의 조합으로 이루어진 task 개수 카운트
#     if num_tasks == 2:
#         count_2_tasks += 1
#         if task_combo_str not in specific_combinations['2tasks']:
#             specific_combinations['2tasks'][task_combo_str] = [folder_name]
#         else:
#             specific_combinations['2tasks'][task_combo_str].append(folder_name)
#     elif num_tasks == 3:
#         count_3_tasks += 1
#         if task_combo_str not in specific_combinations['3tasks']:
#             specific_combinations['3tasks'][task_combo_str] = [folder_name]
#         else:
#             specific_combinations['3tasks'][task_combo_str].append(folder_name)

    

# for key, value in specific_combinations['3tasks'].items():
#     value = random.sample(value, min(50, len(value)))
#     for folder_name in value:
#         src_folder_path = os.path.join(valid_seen_path, folder_name)
#         dst_folder_path = src_folder_path.replace('json_3.0.8', 'json_3.0.9')
        
#         # 대상 경로가 없으면 생성
#         os.makedirs(os.path.dirname(dst_folder_path), exist_ok=True)
        
#         # 폴더 복사
#         if os.path.exists(src_folder_path):
#             shutil.copytree(src_folder_path, dst_folder_path, dirs_exist_ok=True)
#             print(f"Copied: {src_folder_path} -> {dst_folder_path}")
#         else:
#             print(f"Source folder not found: {src_folder_path}")


# # 총 task 조합 개수 출력
# print(f"총 task 조합 개수: {len(task_combinations)}")

# # 2개, 3개, 4개의 조합으로 이루어진 task 개수 출력
# print(f"2개의 조합으로 이루어진 task 개수: {count_2_tasks}")
# for key, value in specific_combinations['2tasks'].items():
#     print(key, ": ", len(value))
# print(f"3개의 조합으로 이루어진 task 개수: {count_3_tasks}")
# for key, value in specific_combinations['3tasks'].items():
#     print(key, ": ", len(value))


# # 총 task 개수 출력
# print(f"총 task 개수: {total_task_combinations}")




























# import os
# from itertools import combinations
# import random
# import shutil
# import json

# # 랜덤 시드 고정
# random.seed(42)

# # 원본 및 새 폴더 경로 설정
# seen_unseen = "valid_unseen"
# source_folder_path = "json_3.0.0/" + seen_unseen
# destination_folder_base = "json_3.0.5"
# destination_folder_path = os.path.join(destination_folder_base, seen_unseen)

# # json_3.0.4 폴더와 valid_seen 폴더가 없다면 생성
# os.makedirs(destination_folder_path, exist_ok=True)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}

# for folder in os.listdir(source_folder_path):
#     # 마지막 '-' 뒤의 숫자가 Floorplan 번호로 추출
#     floorplan_num = folder.split('-')[-1]
    
#     # 가장 처음 '-' 앞의 부분을 task type으로 추출
#     task_type = folder.split('-')[0]
    
#     # 'movable' 단어가 포함된 task는 제외
#     if 'movable' in task_type:
#         continue
    
#     # floorplan number를 키로 하는 딕셔너리 생성
#     if floorplan_num not in floorplan_dict:
#         floorplan_dict[floorplan_num] = []
#     floorplan_dict[floorplan_num].append((task_type, folder))

# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
    
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         # 각 floorplan에 대해 주어진 num_combinations 만큼의 조합 생성
#         for combo in combinations(folders, num_combinations):
#             # pick_heat_then_place_in_recep, pick_cool_then_place_in_recep, pick_clean_then_place_in_recep 중 최소 2개 이상 포함되는지 확인
#             tasks = [task for task, _ in combo]
#             selected_tasks = {'pick_heat_then_place_in_recep', 'pick_cool_then_place_in_recep', 'pick_clean_then_place_in_recep'}
            
#             # selected_tasks에서 최소 2개의 task가 포함되어 있는지 확인
#             if len(selected_tasks.intersection(tasks)) >= 2:
#                 valid, used_trial_folders = is_valid_combination(combo)
#                 if valid:
#                     # 유효한 조합만 저장, 사용된 trial 폴더들도 함께 저장
#                     valid_combinations.append((combo, used_trial_folders))
        
#         all_valid_combinations[floorplan] = valid_combinations
    
#     return all_valid_combinations

# def is_valid_combination(combo):
#     representative_folder_name = combo[0][1]  # 대표 폴더는 첫 번째 폴더
#     trial_folder = os.listdir(os.path.join(source_folder_path, representative_folder_name))[0]
#     representative_traj_data_path = os.path.join(source_folder_path, representative_folder_name, trial_folder, 'traj_data.json')
    
#     # 대표 폴더의 traj_data 로드
#     with open(representative_traj_data_path, 'r') as f:
#         representative_traj_data = json.load(f)
    
#     # 대표 폴더의 object_poses 로드
#     representative_object_poses = representative_traj_data['scene']['object_poses']
#     representative_object_names = [obj['objectName'].split('_')[0] for obj in representative_object_poses]
    
#     used_trial_folders = [trial_folder]  # 사용된 trial 폴더를 저장할 리스트
    
#     for task_type, folder_name in combo[1:]:  # 첫 번째 폴더(대표 폴더)는 제외
#         trial_folders = os.listdir(os.path.join(source_folder_path, folder_name))
#         for trial_folder in trial_folders:
#             traj_data_path = os.path.join(source_folder_path, folder_name, trial_folder, 'traj_data.json')
#             with open(traj_data_path, 'r') as f:
#                 traj_data = json.load(f)
            
#             used_trial_folders.append(trial_folder)  # 사용된 trial 폴더 추가

#             # task_type에 따른 추가 작업 수행
#             if traj_data['task_type'] == 'pick_heat_then_place_in_recep':
#                 heat_levels = ['warm', 'hot', 'boiling']
#                 selected_heat = random.choice(heat_levels)
#                 traj_data['desired_state'] = {'heat': selected_heat}

#             elif traj_data['task_type'] == 'pick_cool_then_place_in_recep':
#                 cool_levels = ['cool', 'cold', 'freezing']
#                 selected_cool = random.choice(cool_levels)
#                 traj_data['desired_state'] = {'cool': selected_cool}

#             elif traj_data['task_type'] == 'pick_clean_then_place_in_recep':
#                 clean_levels = ['rinsed', 'washed']
#                 selected_clean = random.choice(clean_levels)
#                 traj_data['desired_state'] = {'clean': selected_clean}

#             # 수정된 traj_data를 다시 저장
#             with open(traj_data_path, 'w') as f:
#                 json.dump(traj_data, f, indent=4)
        
#         # object_target 가져오기
#         object_target = traj_data['pddl_params']['object_target'].split('_')[0]

#         if task_type == 'pick_two_obj_and_place':
#             # 대표 폴더의 object_poses에 object_target이 2개 이상 포함되어 있는지 확인
#             object_count = representative_object_names.count(object_target)
#             if object_count < 2:
#                 print(f"Object '{object_target}' not found 2 or more times in representative folder '{representative_folder_name}'")
#                 return False, used_trial_folders
#         else:
#             # 대표 폴더의 object_poses에 object_target이 포함되어 있는지 확인
#             if object_target not in representative_object_names:
#                 print(f"Object '{object_target}' not found in representative folder '{representative_folder_name}'")
#                 return False, used_trial_folders

#     # 모든 검사가 통과되면 True 반환
#     return True, used_trial_folders  # valid와 used_trial_folders 반환

# # 2가지, 3가지, 4가지 task의 조합 생성
# combinations_2 = get_combinations(floorplan_dict, 2)
# combinations_3 = get_combinations(floorplan_dict, 3)
# combinations_4 = get_combinations(floorplan_dict, 4)

# # 각 경우의 수에 대해 최대 3개의 조합만 유지하도록 샘플링
# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
    
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
    
#     return sampled_combinations

# # "valid_seen"과 "valid_unseen"에 따른 샘플링 조건 설정
# if "valid_seen" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(combinations_2, max_count=3)
#     sampled_combinations_3 = sample_combinations(combinations_3, max_count=3)
#     sampled_combinations_4 = sample_combinations(combinations_4, max_count=3)
# elif "valid_unseen" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(combinations_2, max_count=50)
#     sampled_combinations_3 = sample_combinations(combinations_3, max_count=50)
#     sampled_combinations_4 = sample_combinations(combinations_4, max_count=35)    


# # 조합한 폴더를 생성하는 함수
# def create_combination_folders(combinations_dict, num_combinations):
#     for floorplan, combos in combinations_dict.items():
#         for combo_data in combos:
#             combo, used_trial_folders = combo_data  # combo와 used_trial_folders를 분리

#             # combo에서 폴더 이름만 추출하여 조합된 폴더 이름 생성
#             combo_folder_name = f"{num_combinations}_" + "__".join([folder_name for _, folder_name in combo])
#             combo_folder_path = os.path.join(destination_folder_path, combo_folder_name)
            
#             # 폴더 생성 (경로가 없다면 생성)
#             os.makedirs(combo_folder_path, exist_ok=True)
            
#             # is_valid_combination 호출로 유효한 조합인지 확인하고 사용된 trial 폴더를 가져옴
#             valid, used_trial_folders = is_valid_combination(combo)

#             if valid:
#                 # 각 combo에서 사용된 trial 폴더들만 복사
#                 for task_type, folder_name in combo:
#                     source_folder = os.path.join(source_folder_path, folder_name)
#                     for trial_folder in used_trial_folders:
#                         source_trial_path = os.path.join(source_folder, trial_folder)
#                         dest_trial_path = os.path.join(combo_folder_path, trial_folder)
#                         if os.path.exists(source_trial_path):
#                             shutil.copytree(source_trial_path, dest_trial_path, dirs_exist_ok=True)

# # 폴더 생성 및 내용물 복사 실행
# create_combination_folders(sampled_combinations_2, 2)
# create_combination_folders(sampled_combinations_3, 3)
# create_combination_folders(sampled_combinations_4, 4)

# print("폴더 생성이 완료되었습니다.")



###############################################################
# import os
# from itertools import combinations
# import random
# import shutil
# import json

# # 랜덤 시드 고정
# random.seed(42)

# # 원본 및 새 폴더 경로 설정
# seen_unseen = "valid_unseen"
# source_folder_path = "json_3.0.0/" + seen_unseen
# destination_folder_base = "json_3.0.4"
# destination_folder_path = os.path.join(destination_folder_base, seen_unseen)

# # json_3.0.3 폴더와 valid_seen 폴더가 없다면 생성
# os.makedirs(destination_folder_path, exist_ok=True)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}

# for folder in os.listdir(source_folder_path):
#     # 마지막 '-' 뒤의 숫자를 floorplan number로 추출
#     floorplan_num = folder.split('-')[-1]
    
#     # 가장 처음 '-' 앞의 부분을 task type으로 추출
#     task_type = folder.split('-')[0]
    
#     # 'movable' 단어가 포함된 task는 제외
#     if 'movable' in task_type:
#         continue
    
#     # floorplan number를 키로 하는 딕셔너리 생성
#     if floorplan_num not in floorplan_dict:
#         floorplan_dict[floorplan_num] = []
#     floorplan_dict[floorplan_num].append((task_type, folder))

# # 특정 조합이 유효한지 확인하는 함수
# def is_valid_combination(combo):
#     representative_folder_name = combo[0][1]  # 대표 폴더는 첫 번째 폴더
#     trial_folder = os.listdir(os.path.join(source_folder_path, representative_folder_name))[0]
#     representative_traj_data_path = os.path.join(source_folder_path, representative_folder_name, trial_folder, 'traj_data.json')
    
#     # 대표 폴더의 traj_data 로드
#     with open(representative_traj_data_path, 'r') as f:
#         representative_traj_data = json.load(f)
    
#     # 대표 폴더의 object_poses 로드
#     representative_object_poses = representative_traj_data['scene']['object_poses']
#     representative_object_names = [obj['objectName'].split('_')[0] for obj in representative_object_poses]
    
#     for task_type, folder_name in combo[1:]:  # 첫 번째 폴더(대표 폴더)는 제외
#         trial_folder = os.listdir(os.path.join(source_folder_path, folder_name))[0]
#         traj_data_path = os.path.join(source_folder_path, folder_name, trial_folder, 'traj_data.json')
        
#         with open(traj_data_path, 'r') as f:
#             traj_data = json.load(f)
        
#         # task_type에 따른 추가 작업 수행
#         if traj_data['task_type'] == 'pick_heat_then_place_in_recep':
#             heat_levels = ['warm', 'hot', 'boiling']
#             selected_heat = random.choice(heat_levels)
#             traj_data['desired_state'] = {'heat': selected_heat}

#         elif traj_data['task_type'] == 'pick_cool_then_place_in_recep':
#             cool_levels = ['cool', 'cold', 'freezing']
#             selected_cool = random.choice(cool_levels)
#             traj_data['desired_state'] = {'cool': selected_cool}

#         elif traj_data['task_type'] == 'pick_clean_then_place_in_recep':
#             clean_levels = ['rinsed', 'washed']
#             selected_clean = random.choice(clean_levels)
#             traj_data['desired_state'] = {'clean': selected_clean}

#         # 수정된 traj_data를 다시 저장
#         with open(traj_data_path, 'w') as f:
#             json.dump(traj_data, f, indent=4)
        
#         # object_target 가져오기
#         object_target = traj_data['pddl_params']['object_target'].split('_')[0]

#         if task_type == 'pick_two_obj_and_place':
#             # 대표 폴더의 object_poses에 object_target이 2개 이상 포함되어 있는지 확인
#             object_count = representative_object_names.count(object_target)
#             if object_count < 2:
#                 print(f"Object '{object_target}' not found 2 or more times in representative folder '{representative_folder_name}'")
#                 return False
#         else:
#             # 대표 폴더의 object_poses에 object_target이 포함되어 있는지 확인
#             if object_target not in representative_object_names:
#                 print(f"Object '{object_target}' not found in representative folder '{representative_folder_name}'")
#                 return False

#     # 모든 검사가 통과되면 True 반환
#     return True


# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
    
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         # 각 floorplan에 대해 주어진 num_combinations 만큼의 조합 생성
#         for combo in combinations(folders, num_combinations):
#             # pick_heat_then_place_in_recep, pick_cool_then_place_in_recep, pick_clean_then_place_in_recep 중 최소 2개 이상 포함되는지 확인
#             tasks = [task for task, _ in combo]
#             selected_tasks = {'pick_heat_then_place_in_recep', 'pick_cool_then_place_in_recep', 'pick_clean_then_place_in_recep'}
            
#             # selected_tasks에서 최소 2개의 task가 포함되어 있는지 확인
#             if len(selected_tasks.intersection(tasks)) >= 2:
#                 if is_valid_combination(combo):
#                     valid_combinations.append(combo)
        
#         all_valid_combinations[floorplan] = valid_combinations
    
#     return all_valid_combinations
# # 2가지, 3가지, 4가지 task의 조합 생성
# combinations_2 = get_combinations(floorplan_dict, 2)
# combinations_3 = get_combinations(floorplan_dict, 3)
# combinations_4 = get_combinations(floorplan_dict, 4)

# # 각 경우의 수에 대해 최대 3개의 조합만 유지하도록 샘플링
# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
    
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
    
#     return sampled_combinations

# if "valid_seen" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(combinations_2, max_count=3)
#     sampled_combinations_3 = sample_combinations(combinations_3, max_count=3)
#     sampled_combinations_4 = sample_combinations(combinations_4, max_count=3)
# elif "valid_unseen" in destination_folder_path:
#     sampled_combinations_2 = sample_combinations(combinations_2, max_count=50)
#     sampled_combinations_3 = sample_combinations(combinations_3, max_count=50)
#     sampled_combinations_4 = sample_combinations(combinations_4, max_count=35)    

# # 조합한 폴더를 생성하는 함수
# def create_combination_folders(combinations_dict, num_combinations):
#     for floorplan, combos in combinations_dict.items():
#         for combo in combos:
#             # 조합된 폴더 이름 생성
#             combo_folder_name = f"{num_combinations}_" + "__".join([task[1] for task in combo])
#             combo_folder_path = os.path.join(destination_folder_path, combo_folder_name)
            
#             # 폴더 생성 (경로가 없다면 생성)
#             os.makedirs(combo_folder_path, exist_ok=True)
            
#             # 조합된 각 폴더의 파일들을 새 폴더에 복사
#             for task_type, folder_name in combo:
#                 source_folder = os.path.join(source_folder_path, folder_name)
#                 for item in os.listdir(source_folder):
#                     s = os.path.join(source_folder, item)
#                     d = os.path.join(combo_folder_path, item)
#                     if os.path.isdir(s):
#                         shutil.copytree(s, d, dirs_exist_ok=True)
#                     else:
#                         shutil.copy2(s, d)

# # 폴더 생성 및 내용물 복사 실행
# create_combination_folders(sampled_combinations_2, 2)
# create_combination_folders(sampled_combinations_3, 3)
# create_combination_folders(sampled_combinations_4, 4)

# print("폴더 생성이 완료되었습니다.")



























##### json_3.0.2 #####
# import os
# from itertools import combinations
# import random
# import shutil

# # 원본 및 새 폴더 경로 설정
# source_folder_path = "json_3.0.0/valid_seen"
# destination_folder_path = "json_3.0.2"

# # json_3.0.2 폴더가 없다면 생성
# if not os.path.exists(destination_folder_path):
#     os.makedirs(destination_folder_path)

# # 폴더 내의 모든 폴더 이름 가져오기
# all_folders = os.listdir(source_folder_path)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}

# for folder in all_folders:
#     # 마지막 '-' 뒤의 숫자를 floorplan number로 추출
#     floorplan_num = folder.split('-')[-1]
    
#     # 가장 처음 '-' 앞의 부분을 task type으로 추출
#     task_type = folder.split('-')[0]
    
#     # 'movable' 단어가 포함된 task는 제외
#     if 'movable' in task_type:
#         continue
    
#     # floorplan number를 키로 하는 딕셔너리 생성
#     if floorplan_num not in floorplan_dict:
#         floorplan_dict[floorplan_num] = []
#     floorplan_dict[floorplan_num].append((task_type, folder))

# # 조합 가능한 폴더 쌍의 수 계산 함수
# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
    
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         # 각 floorplan에 대해 주어진 num_combinations 만큼의 조합 생성
#         for combo in combinations(folders, num_combinations):
#             # 적어도 하나의 task가 pick_cool_then_place_in_recep 또는 pick_heat_then_place_in_recep 인지 확인
#             task_types = [task[0] for task in combo]
#             if "pick_cool_then_place_in_recep" in task_types or "pick_heat_then_place_in_recep" in task_types:
#                 valid_combinations.append(combo)
        
#         all_valid_combinations[floorplan] = valid_combinations
    
#     return all_valid_combinations

# # 2가지, 3가지, 4가지 task의 조합 생성
# combinations_2 = get_combinations(floorplan_dict, 2)
# combinations_3 = get_combinations(floorplan_dict, 3)
# combinations_4 = get_combinations(floorplan_dict, 4)

# # 각 경우의 수에 대해 최대 3개의 조합만 유지하도록 샘플링
# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
    
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
    
#     return sampled_combinations

# sampled_combinations_2 = sample_combinations(combinations_2, max_count=3)
# sampled_combinations_3 = sample_combinations(combinations_3, max_count=3)
# sampled_combinations_4 = sample_combinations(combinations_4, max_count=3)

# # 조합한 폴더를 생성하는 함수
# def create_combination_folders(combinations_dict, num_combinations):
#     for floorplan, combos in combinations_dict.items():
#         for combo in combos:
#             # 조합된 폴더 이름 생성
#             combo_folder_name = f"{num_combinations}_" + "__".join([task[1] for task in combo])
#             combo_folder_path = os.path.join(destination_folder_path, combo_folder_name)
            
#             # 폴더 생성 (이미 존재하지 않는 경우에만)
#             if not os.path.exists(combo_folder_path):
#                 os.makedirs(combo_folder_path)
            
#             # 조합된 각 폴더의 파일들을 새 폴더에 복사
#             for task_type, folder_name in combo:
#                 source_folder = os.path.join(source_folder_path, folder_name)
#                 for item in os.listdir(source_folder):
#                     s = os.path.join(source_folder, item)
#                     d = os.path.join(combo_folder_path, item)
#                     if os.path.isdir(s):
#                         shutil.copytree(s, d, dirs_exist_ok=True)
#                     else:
#                         shutil.copy2(s, d)

# # 폴더 생성 및 내용물 복사 실행
# create_combination_folders(sampled_combinations_2, 2)
# create_combination_folders(sampled_combinations_3, 3)
# create_combination_folders(sampled_combinations_4, 4)

# print("폴더 생성이 완료되었습니다.")












# import os
# from itertools import combinations
# import random

# # 폴더 경로 설정
# folder_path = "json_3.0.0/valid_seen"

# # 폴더 내의 모든 폴더 이름 가져오기
# all_folders = os.listdir(folder_path)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}

# for folder in all_folders:
#     # 마지막 '-' 뒤의 숫자를 floorplan number로 추출
#     floorplan_num = folder.split('-')[-1]
    
#     # 가장 처음 '-' 앞의 부분을 task type으로 추출
#     task_type = folder.split('-')[0]
    
#     # 'movable' 단어가 포함된 task는 제외
#     if 'movable' in task_type:
#         continue
    
#     # floorplan number를 키로 하는 딕셔너리 생성
#     if floorplan_num not in floorplan_dict:
#         floorplan_dict[floorplan_num] = []
#     floorplan_dict[floorplan_num].append((task_type, folder))

# # 조합 가능한 폴더 쌍의 수 계산 함수
# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
    
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         # 각 floorplan에 대해 주어진 num_combinations 만큼의 조합 생성
#         for combo in combinations(folders, num_combinations):
#             # 적어도 하나의 task가 pick_cool_then_place_in_recep 또는 pick_heat_then_place_in_recep 인지 확인
#             task_types = [task[0] for task in combo]
#             if "pick_cool_then_place_in_recep" in task_types or "pick_heat_then_place_in_recep" in task_types:
#                 valid_combinations.append(combo)
        
#         all_valid_combinations[floorplan] = valid_combinations
    
#     return all_valid_combinations

# # 2가지, 3가지, 4가지 task의 조합 생성
# combinations_2 = get_combinations(floorplan_dict, 2)
# combinations_3 = get_combinations(floorplan_dict, 3)
# combinations_4 = get_combinations(floorplan_dict, 4)

# # 각 경우의 수에 대해 최대 3개의 조합만 유지하도록 샘플링
# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
    
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
    
#     return sampled_combinations

# sampled_combinations_2 = sample_combinations(combinations_2, max_count=3)
# sampled_combinations_3 = sample_combinations(combinations_3, max_count=3)
# sampled_combinations_4 = sample_combinations(combinations_4, max_count=3)

# # 결과 출력
# print(f"2가지 task 조합의 경우의 수 (최대 3개): {sum(len(combos) for combos in sampled_combinations_2.values())}")
# print(f"3가지 task 조합의 경우의 수 (최대 3개): {sum(len(combos) for combos in sampled_combinations_3.values())}")
# print(f"4가지 task 조합의 경우의 수 (최대 3개): {sum(len(combos) for combos in sampled_combinations_4.values())}")












# import os
# from itertools import combinations
# import random
# import shutil

# # 폴더 경로 설정
# source_folder_path = "json_3.0.0/valid_seen"
# target_folder_path = "json_3.0.1"

# # 타겟 폴더 생성 (이미 존재하면 건너뜀)
# os.makedirs(target_folder_path, exist_ok=True)

# # 폴더 내의 모든 폴더 이름 가져오기
# all_folders = os.listdir(source_folder_path)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}

# for folder in all_folders:
#     # 마지막 '-' 뒤의 숫자를 floorplan number로 추출
#     floorplan_num = folder.split('-')[-1]
    
#     # 가장 처음 '-' 앞의 부분을 task type으로 추출
#     task_type = folder.split('-')[0]
    
#     # floorplan number를 키로 하는 딕셔너리 생성
#     if floorplan_num not in floorplan_dict:
#         floorplan_dict[floorplan_num] = []
#     floorplan_dict[floorplan_num].append((task_type, folder))

# # 조합 가능한 폴더 쌍의 수 계산 함수
# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
    
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         # 각 floorplan에 대해 주어진 num_combinations 만큼의 조합 생성
#         for combo in combinations(folders, num_combinations):
#             # 적어도 하나의 task가 pick_cool_then_place_in_recep 또는 pick_heat_then_place_in_recep 인지 확인
#             task_types = [task[0] for task in combo]
#             if "pick_cool_then_place_in_recep" in task_types or "pick_heat_then_place_in_recep" in task_types:
#                 valid_combinations.append(combo)
        
#         all_valid_combinations[floorplan] = valid_combinations
    
#     return all_valid_combinations

# # 2가지, 3가지, 4가지 task의 조합 생성
# combinations_2 = get_combinations(floorplan_dict, 2)
# combinations_3 = get_combinations(floorplan_dict, 3)
# combinations_4 = get_combinations(floorplan_dict, 4)

# # 각 경우의 수에 대해 최대 3개의 조합만 유지하도록 샘플링
# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
    
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
    
#     return sampled_combinations

# sampled_combinations_2 = sample_combinations(combinations_2, max_count=3)
# sampled_combinations_3 = sample_combinations(combinations_3, max_count=3)
# sampled_combinations_4 = sample_combinations(combinations_4, max_count=3)

# # 새로운 조합된 폴더 생성
# def create_combination_folders(sampled_combinations, num_combinations):
#     for floorplan, combos in sampled_combinations.items():
#         for combo in combos:
#             # 새로운 폴더 이름 생성
#             folder_name = f"{num_combinations}_" + "__".join([task[1] for task in combo])
#             new_folder_path = os.path.join(target_folder_path, folder_name)
            
#             # 새로운 폴더 생성
#             os.makedirs(new_folder_path, exist_ok=True)
            
#             # 각 폴더의 파일들을 새로운 폴더로 복사
#             for task_type, original_folder in combo:
#                 original_folder_path = os.path.join(source_folder_path, original_folder)
#                 for item in os.listdir(original_folder_path):
#                     source_item_path = os.path.join(original_folder_path, item)
#                     destination_item_path = os.path.join(new_folder_path, item)
                    
#                     if os.path.isdir(source_item_path):
#                         shutil.copytree(source_item_path, destination_item_path, dirs_exist_ok=True)
#                     else:
#                         shutil.copy2(source_item_path, destination_item_path)

# # 조합된 폴더 생성
# create_combination_folders(sampled_combinations_2, 2)
# create_combination_folders(sampled_combinations_3, 3)
# create_combination_folders(sampled_combinations_4, 4)

# print("조합된 폴더들이 json_3.0.1 폴더에 생성되었습니다.")









# import os
# from itertools import combinations
# import random

# # 폴더 경로 설정
# folder_path = "json_3.0.0/valid_seen"

# # 폴더 내의 모든 폴더 이름 가져오기
# all_folders = os.listdir(folder_path)

# # 폴더를 floorplan number로 그룹화
# floorplan_dict = {}

# for folder in all_folders:
#     # 마지막 '-' 뒤의 숫자를 floorplan number로 추출
#     floorplan_num = folder.split('-')[-1]
    
#     # 가장 처음 '-' 앞의 부분을 task type으로 추출
#     task_type = folder.split('-')[0]
    
#     # floorplan number를 키로 하는 딕셔너리 생성
#     if floorplan_num not in floorplan_dict:
#         floorplan_dict[floorplan_num] = []
#     floorplan_dict[floorplan_num].append((task_type, folder))

# # 조합 가능한 폴더 쌍의 수 계산 함수
# def get_combinations(floorplan_dict, num_combinations):
#     all_valid_combinations = {}
    
#     for floorplan, folders in floorplan_dict.items():
#         valid_combinations = []
#         # 각 floorplan에 대해 주어진 num_combinations 만큼의 조합 생성
#         for combo in combinations(folders, num_combinations):
#             # 적어도 하나의 task가 pick_cool_then_place_in_recep 또는 pick_heat_then_place_in_recep 인지 확인
#             task_types = [task[0] for task in combo]
#             if "pick_cool_then_place_in_recep" in task_types or "pick_heat_then_place_in_recep" in task_types:
#                 valid_combinations.append(combo)
        
#         all_valid_combinations[floorplan] = valid_combinations
    
#     return all_valid_combinations

# # 2가지, 3가지, 4가지 task의 조합 생성
# combinations_2 = get_combinations(floorplan_dict, 2)
# combinations_3 = get_combinations(floorplan_dict, 3)
# combinations_4 = get_combinations(floorplan_dict, 4)

# # 각 경우의 수에 대해 최대 3개의 조합만 유지하도록 샘플링
# def sample_combinations(combinations_dict, max_count=3):
#     sampled_combinations = {}
    
#     for floorplan, combos in combinations_dict.items():
#         if len(combos) > max_count:
#             sampled_combinations[floorplan] = random.sample(combos, max_count)
#         else:
#             sampled_combinations[floorplan] = combos
    
#     return sampled_combinations

# sampled_combinations_2 = sample_combinations(combinations_2, max_count=3)
# sampled_combinations_3 = sample_combinations(combinations_3, max_count=3)
# sampled_combinations_4 = sample_combinations(combinations_4, max_count=3)

# # 결과 출력
# print(f"2가지 task 조합의 경우의 수 (최대 3개): {sum(len(combos) for combos in sampled_combinations_2.values())}")
# print(f"3가지 task 조합의 경우의 수 (최대 3개): {sum(len(combos) for combos in sampled_combinations_3.values())}")
# print(f"4가지 task 조합의 경우의 수 (최대 3개): {sum(len(combos) for combos in sampled_combinations_4.values())}")