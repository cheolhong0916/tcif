# Function to generate the minimum action sequence for each task
def get_shortest_action_sequence(G, tasks_):
    action_sequences = []
    tasks_ = [['pick_heat_then_place_in_recep', 'Apple', 'Fridge', 'boiling', 120, 'microwave'],
             ['pick_clean_then_place_in_recep', 'Mug', 'CoffeeMachine', 'washed', 40, 'sinkbasin'],
             ['pick_cool_then_place_in_recep', 'Cup', 'SinkBasin', 'cool', 120, 'fridge'],
             ['pick_and_place_simple',         'Bread', 'Countertop', 'none', 1, 'none']]
    all_permutations = [list(p) for p in permutations(tasks_)]

    for tasks in all_permutations:
        actions, total_time = check_feasibility(G, 'spawned_location', tasks, task_num=1, total_actions=[], total_time=0, started_tasks=[])
        action_sequences.append((total_time, actions))

    action_sequences = sorted(action_sequences)

    return action_sequences[0][1], action_sequences[0][0]   # actions, total_time





def check_feasibility(G, last_node, tasks, task_num, total_actions, total_time, started_tasks):
    # If there are no tasks left to process, return accumulated actions and time
    if task_num >= len(tasks) and not started_tasks:
        return total_actions, total_time
    
    # Identify the current task and the prior task if available
    current_task = tasks[task_num] if task_num < len(tasks) else None

    # Go to the current task's milestone if it exists
    if current_task:
        if len(started_tasks) > 0 :

            actions, time_taken, updated_node = execute_actions(G, last_node, current_task, start=True)
            _, time_taken_to_go_back = get_shortest_path_distance(G, updated_node, last_node)

            # Check if starting the next task would exceed the time boundary
            if time_taken + time_taken_to_go_back > started_tasks[0][0]:

                # Complete the task as the time boundary allows
                if started_tasks[0][1] > 0:
                    total_actions.append(f"wait for {started_tasks[0][1]} time steps")
                    total_time += started_tasks[0][1]
                    started_tasks = update_priority_queue(started_tasks, started_tasks[0][1])
                actions, time_taken, updated_node = execute_actions(G, last_node, started_tasks[0][2], start=False)
                total_actions.extend(actions)
                total_time += time_taken
                started_tasks = update_priority_queue(started_tasks, time_taken)
                _, _, _ = heapq.heappop(started_tasks)

                total_actions_, total_time_ = check_feasibility(G, updated_node, tasks, task_num, total_actions, total_time, started_tasks)
                if total_actions_:
                    total_actions = total_actions_; total_time = total_time_


            else:
                # We can start the new task and add it to the queue of started tasks
                actions, time_taken, updated_node = execute_actions(G, last_node, current_task, start=True)
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
            actions, time_taken, updated_node = execute_actions(G, last_node, current_task, start=True)
            total_actions.extend(actions)
            total_time += time_taken
            heapq.heappush(started_tasks, (TIME_BOUNDARIES[current_task[3]][1], TIME_BOUNDARIES[current_task[3]][0], current_task))

            total_actions, total_time = check_feasibility(
                G, updated_node, tasks, task_num + 1, total_actions, total_time, started_tasks
            )

    else:
        breakpoint()

    return total_actions, total_time


