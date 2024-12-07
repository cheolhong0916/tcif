import os
from collections import Counter

# 경로 설정
valid_seen_path = "json_3.0.8/train_3tasks"

# 폴더 내의 모든 폴더 이름 가져오기
folders = os.listdir(valid_seen_path)

# Floorplan 번호를 추출하고 고유한 Floorplan 개수 계산
floorplans = set()
for folder_name in folders:
    if not os.path.exists(os.path.join(valid_seen_path, folder_name, 'expert_demo.json')):
        continue
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

for folder_name in folders:
    if not os.path.exists(os.path.join(valid_seen_path, folder_name, 'expert_demo.json')):
        continue
    # 폴더 이름에서 task type들을 추출
    tasks = folder_name.split('__')
    
    # task type 카운트와 조합 생성
    task_combo = tuple(sorted(Counter([task.split('-')[0] for task in tasks if task.split('-')[0] in task_types]).items()))
    task_combinations.add(task_combo)

    # 조합된 task의 개수 세기
    num_tasks = len(tasks)

    # 총 task 조합 개수 업데이트
    total_task_combinations += 1

    # 2개, 3개, 4개의 조합으로 이루어진 task 개수 카운트
    if num_tasks == 2:
        count_2_tasks += 1
    elif num_tasks == 3:
        count_3_tasks += 1
    elif num_tasks == 4:
        count_4_tasks += 1

# 총 task 조합 개수 출력
print(f"총 task 조합 개수: {len(task_combinations)}")

# 2개, 3개, 4개의 조합으로 이루어진 task 개수 출력
print(f"2개의 조합으로 이루어진 task 개수: {count_2_tasks}")
print(f"3개의 조합으로 이루어진 task 개수: {count_3_tasks}")
print(f"4개의 조합으로 이루어진 task 개수: {count_4_tasks}")

# 총 task 개수 출력
print(f"총 task 개수: {total_task_combinations}")