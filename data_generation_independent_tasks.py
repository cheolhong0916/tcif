import os
import shutil

def copy_non_overlapping_folders(src_root, dst_root):
    """
    조건에 맞는 폴더와 내용을 복사합니다.

    :param src_root: 원본 폴더 경로 (예: json_3.0.7)
    :param dst_root: 복사 대상 폴더 경로 (예: json_3.0.8)
    """
    if not os.path.exists(dst_root):
        os.makedirs(dst_root)

    folder_counts = {}  # 각 subdir의 폴더 개수를 저장하는 딕셔너리

    # valid_seen, valid_unseen, train 디렉토리 순회
    for subdir in ["valid_seen", "valid_unseen", "train"]:
        src_dir = os.path.join(src_root, subdir)
        dst_dir = os.path.join(dst_root, subdir)

        if not os.path.exists(src_dir):
            print(f"Source directory {src_dir} does not exist. Skipping.")
            continue

        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)

        copied_count = 0  # 현재 subdir에서 복사된 폴더 수

        for folder_name in os.listdir(src_dir):
            src_folder_path = os.path.join(src_dir, folder_name)

            # 폴더 이름에서 target objects 파싱
            try:
                parts = folder_name.split("__")
                target_objects = [task.split("-")[1] for task in parts]
            except IndexError:
                print(f"Skipping invalid folder name: {folder_name}")
                continue

            # target objects 겹침 여부 확인
            if len(target_objects) != len(set(target_objects)):
                print(f"Skipping folder with overlapping objects: {folder_name}")
                continue

            # 대상 경로 생성 및 폴더 복사
            dst_folder_path = os.path.join(dst_dir, folder_name)
            if not os.path.exists(dst_folder_path):
                shutil.copytree(src_folder_path, dst_folder_path)
                copied_count += 1
                print(f"Copied {src_folder_path} to {dst_folder_path}")

        # 현재 subdir에서 복사된 폴더 개수를 저장
        folder_counts[subdir] = copied_count

    # 각 subdir의 폴더 개수 출력
    print("\nSummary:")
    for subdir, count in folder_counts.items():
        print(f"{subdir}: {count} folders copied.")

if __name__ == "__main__":
    # 원본 및 대상 경로 설정
    source_root = "json_3.0.7"
    destination_root = "json_3.0.8"

    # 복사 실행
    copy_non_overlapping_folders(source_root, destination_root)