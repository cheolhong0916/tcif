import os
import shutil
from tqdm import trange

# 경로 설정
src_dir = '/home/cheolhong/ch/alfworld/json_2.1.3'
dst_dir = '/home/cheolhong/ch/alfworld/json_2.1.4'
special_src_dir = '/home/cheolhong/ch/alfworld/json_2.1.1'  # trial_ 폴더에만 적용

# json_2.1.4 디렉토리가 없으면 생성
os.makedirs(dst_dir, exist_ok=True)

# trial_ 폴더에서 추가로 복사할 파일들
additional_files = ["game.tw-pddl", "initial_state.pddl"]

# src_dir 내부를 순회
all_dirs = list(os.walk(src_dir))  # 전체 디렉토리 목록을 미리 가져옵니다.
for i in trange(len(all_dirs), desc="Copying Files", unit="dir"):
    root, dirs, files = all_dirs[i]
    relative_path = os.path.relpath(root, src_dir)
    dst_path = os.path.join(dst_dir, relative_path)
    
    # json_2.1.3 내의 모든 파일을 json_2.1.4에 동일한 경로로 복사
    os.makedirs(dst_path, exist_ok=True)
    for file_name in files:
        src_file_path = os.path.join(root, file_name)
        shutil.copy(src_file_path, dst_path)
    
    # trial_로 시작하는 폴더의 경우 추가 파일을 json_2.1.1 경로에서 복사
    if os.path.basename(root).startswith("trial_"):
        special_root = os.path.join(special_src_dir, relative_path)
        
        for file_name in additional_files:
            special_file_path = os.path.join(special_root, file_name)
            if os.path.exists(special_file_path):
                shutil.copy(special_file_path, dst_path)