import pandas as pd
from ortools.sat.python import cp_model


def plan(teacher_subjects, subjects_required, teacher_required={}):
    # 教师
    teacher_list = list(teacher_subjects.keys())

    # 班级数
    class_list = list(subjects_required.keys())

    # 课程
    subjects_set = set()
    for subject_required in subjects_required.values():
        subjects_set.update(subject_required.keys())
    subject_list = list(subjects_set)

    # 建模
    model = cp_model.CpModel()

    # 决策变量：教师i在班级j的第k天第l个课时教授课程m
    x = {}
    for teacher in teacher_list:
        for class_ in class_list:
            for day in range(6):
                for period in range(9):
                    for subject in subject_list:
                        x[teacher, class_, day, period, subject] = model.NewBoolVar(
                            f"x[{teacher}, {class_}, {day}, {period}, {subject}]"
                        )
    # model.Add(x['郑成功', '高三1班', 3, 8, '体育'] == 1)

    # 辅助变量：是否和下一节课连续
    consecutive = {}
    for teacher in teacher_list:
        for class_ in class_list:
            for day in range(6):
                for period in range(8):
                    for subject in subject_list:
                        consecutive[teacher, class_, day, period, subject] = (
                            model.NewBoolVar(
                                f"consecutive[{teacher}, {class_}, {day}, {period}, {subject}]"
                            )
                        )

    # 辅助变量：教师在上午或下午是否有课
    teacher_morning = {}
    teacher_afternoon = {}
    for teacher in teacher_list:
        for day in range(6):
            teacher_morning[teacher, day] = model.NewBoolVar(f'morning_{teacher}_{day}')
            teacher_afternoon[teacher, day] = model.NewBoolVar(f'afternoon_{teacher}_{day}')


    # 约束条件：每个老师只能给固定的班级授课
    for class_ in class_list:
        class_teacher_list = teacher_required.get(class_, {}).values()
        for teacher in teacher_list:
            for subject in subject_list:
                if teacher not in class_teacher_list:
                    model.Add(
                        sum(
                            x[teacher, class_, day, period, subject]
                            for day in range(6)
                            for period in range(9)
                        ) == 0
                    )
    # 约束条件：每个老师只教授固定的课程
    for teacher in teacher_list:
        for class_ in class_list:
            for day in range(6):
                for period in range(9):
                    for subject in subject_list:
                        if subject not in teacher_subjects[teacher]:
                            model.Add(x[teacher, class_, day, period, subject] == 0)

    # 约束条件：每个班级的课时数固定
    for class_ in class_list:
        for subject in subject_list:
            model.Add(
                sum(
                    x[teacher, class_, day, period, subject]
                    for teacher in teacher_list
                    for day in range(6)
                    for period in range(9)
                ) == subjects_required[class_].get(subject, 0)
            )

    # 约束条件：每个老师在每天相同时段只能出现一次
    for teacher in teacher_list:
        for day in range(6):
            for period in range(9):
                model.Add(
                    sum(
                        x[teacher, class_, day, period, subject]
                        for class_ in class_list
                        for subject in subject_list
                    ) <= 1
                )
    # 约束条件：每个班级相同时段只能有一个课程
    for class_ in class_list:
        for day in range(6):
            for period in range(9):
                model.Add(
                    sum(
                        x[teacher, class_, day, period, subject]
                        for teacher in teacher_list
                        for subject in subject_list
                    ) <= 1
                )

    # 约束条件：体育课不能排在上午前两节
    for teacher in teacher_list:
        for class_ in class_list:
            for day in range(6):
                for period in range(2):  # 前两节课
                    model.Add(x[teacher, class_, day, period, '体育'] == 0)

    # 约束条件：体育课只能排在周 456
    for teacher in teacher_list:
        for class_ in class_list:
            for day in range(3):  # 周一、二、三
                for period in range(9):
                    model.Add(x[teacher, class_, day, period, '体育'] == 0)

    # 约束条件：每天的第一节、第二节和第六节必须排课
    for class_ in class_list:
        for day in range(6):
            for period in [0, 1, 5]:  # 第一节、第二节和第六节
                model.Add(sum(x[teacher, class_, day, period, subject]
                            for teacher in teacher_list
                            for subject in subject_list) == 1)

    # 约束条件：如果课程数大于6-每天最多上2节，如果课程数小于6-每天最多上1节
    for class_ in class_list:
        for subject in subject_list:
            for day in range(6):
                subject_count = subjects_required[class_].get(subject, 0)
                lesson_count = sum(
                            x[teacher, class_, day, period, subject]
                            for teacher in teacher_list
                            for period in range(9)
                        )
                if subject_count > 6:
                    model.Add(lesson_count >= 1)
                    model.Add(lesson_count <= 2)
                else:
                    model.Add(lesson_count <= 1)

    # 约束条件：如果班级当天课程等于2，那么这2节课程必须连续，并且不能在第5节和第6节
    for teacher in teacher_list:
        for class_ in class_list:
            for day in range(6):
                for subject in subject_list:
                    # 计算这门课在这一天的总课程数
                    total_lessons = sum(
                        x[teacher, class_, day, period, subject] for period in range(9)
                    )
                    # 1. 如果有两节课，必须连续
                    # 创建变量，是否和下一节课连续
                    consecutive_sum = sum(
                        consecutive[teacher, class_, day, period, subject]
                        for period in range(8)
                    )
                    # 2 节课，consecutive_sum 为 1
                    # 1 节课，consecutive_sum 为 0
                    # 0 节课，consecutive_sum 为 0
                    model.Add(consecutive_sum >= total_lessons - 1)
                    # 连续性约束
                    for period in range(8):
                        # 连续性为真时，两节课都为真
                        model.add_bool_and([
                                x[teacher, class_, day, period, subject],
                                x[teacher, class_, day, period + 1, subject],
                        ]).only_enforce_if(
                            consecutive[teacher, class_, day, period, subject]
                        )
                        # 连续性为假时，至少有一节为假
                        model.AddBoolOr(
                            [
                                x[teacher, class_, day, period, subject].Not(),
                                x[teacher, class_, day, period + 1, subject].Not(),
                            ]
                        ).OnlyEnforceIf(
                            consecutive[teacher, class_, day, period, subject].Not()
                        )
                    # 3. 不能在第5节和第6节安排连续的两节课
                    model.Add(x[teacher, class_, day, 4, subject] + x[teacher, class_, day, 5, subject] <= 1)

    # 约束条件，尽量避免在周六安排连堂课
    # 创建用于记录惩罚变量的列表
    penalty = {}  # 用于存储每个班级和课程的惩罚变量
    penalty_weight = 100  # 惩罚权重

    for class_ in class_list:
        for subject in subject_list:
            # 正确统计每个时段的课程情况
            saturday_classes = []
            for period in range(9):
                period_sum = []
                for teacher in teacher_list:
                    period_sum.append(x[teacher, class_, 5, period, subject])
                # 每个时段最多只有一节课
                saturday_classes.append(sum(period_sum))

            # 创建布尔惩罚变量
            penalty[class_, subject] = model.NewBoolVar(f"penalty[{class_}, {subject}]")

            # 正确的布尔约束：当课程数量>=2时，penalty为1；否则为0
            model.Add(sum(saturday_classes) >= 2).OnlyEnforceIf(penalty[class_, subject])
            model.Add(sum(saturday_classes) < 2).OnlyEnforceIf(penalty[class_, subject].Not())

    # 目标函数：最小化惩罚项的总和
    model.Minimize(sum(penalty[class_, subject] for class_ in class_list for subject in subject_list) * penalty_weight)

    # 约束条件，周1、3、5语文尽量靠前，周2、4、6英语尽量靠前
    # objective_terms = []
    # for class_ in class_list:
    #     for day in range(6):
    #         if day % 2 == 0:
    #             # 周1、3、5， 语文课尽量靠前
    #             teacher = teacher_required.get(class_, {}).get('语文')
    #             for period in range(9):
    #                 objective_terms.append(x[teacher, class_, day, period, '语文'] * period)
    #         else:
    #             # 周2、4、6，英语课尽量靠前
    #             teacher = teacher_required.get(class_, {}).get('英语')
    #             for period in range(9):
    #                 objective_terms.append(x[teacher, class_, day, period, '英语'] * period)
    # model.minimize(sum(objective_terms))


    # 约束条件：教师当天的课程尽量全部在上午或全部在下午
    morning_periods = range(5) # 0-4 为上午时间段
    afternoon_periods = range(5, 9)  # 5-8 为下午时间段
    time_block_penalties = []
    for teacher in teacher_list:
        for day in range(6):
            # 检测上午是否有课
            morning_classes = []
            for period in morning_periods:
                for class_ in class_list:
                    for subject in subject_list:
                        morning_classes.append(x[teacher, class_, day, period, subject])
            model.AddBoolOr(morning_classes).OnlyEnforceIf(teacher_morning[teacher, day])
            model.AddBoolAnd([v.Not() for v in morning_classes]).OnlyEnforceIf(teacher_morning[teacher, day].Not())

            # 检测下午是否有课
            afternoon_classes = []
            for period in afternoon_periods:
                for class_ in class_list:
                    for subject in subject_list:
                        afternoon_classes.append(x[teacher, class_, day, period, subject])
            model.AddBoolOr(afternoon_classes).OnlyEnforceIf(teacher_afternoon[teacher, day])
            model.AddBoolAnd([v.Not() for v in afternoon_classes]).OnlyEnforceIf(teacher_afternoon[teacher, day].Not())

            # 创建时间块惩罚变量
            time_block_penalty = model.NewBoolVar(f'time_block_penalty_{teacher}_{day}')
            model.AddBoolAnd([teacher_morning[teacher, day],
                              teacher_afternoon[teacher, day]]).OnlyEnforceIf(time_block_penalty)
            model.AddBoolOr([teacher_morning[teacher, day].Not(),
                             teacher_afternoon[teacher, day].Not()]).OnlyEnforceIf(time_block_penalty.Not())

            time_block_penalties.append(time_block_penalty)
    # === 第二部分：周1、3、5语文尽量靠前，周2、4、6英语尽量靠前 ===
    subject_time_costs = []

    for class_ in class_list:
        for day in range(6):
            for period in range(9):
                for teacher in teacher_list:
                    # 语文课在周1、3、5的权重
                    if day in [0, 2, 4]:  # 周1、3、5
                        for subject in subject_list:
                            if subject == "语文":
                                # 创建整型变量表示课程位置的代价
                                cost = model.NewIntVar(0, period, f'chinese_cost_{class_}_{day}_{period}')
                                # 如果这个时间段安排了语文课，代价等于period值（越往后代价越大）
                                model.Add(cost == period).OnlyEnforceIf(x[teacher, class_, day, period, subject])
                                model.Add(cost == 0).OnlyEnforceIf(x[teacher, class_, day, period, subject].Not())
                                subject_time_costs.append(cost)

                    # 英语课在周2、4、6的权重
                    if day in [1, 3, 5]:  # 周2、4、6
                        for subject in subject_list:
                            if subject == "英语":
                                cost = model.NewIntVar(0, period, f'english_cost_{class_}_{day}_{period}')
                                model.Add(cost == period).OnlyEnforceIf(x[teacher, class_, day, period, subject])
                                model.Add(cost == 0).OnlyEnforceIf(x[teacher, class_, day, period, subject].Not())
                                subject_time_costs.append(cost)

    # === 组合两个优化目标 ===
    # 将时间块惩罚转换为整数值并设置权重
    time_block_cost = sum(time_block_penalties) * 100  # 给较大权重确保这是主要优化目标

    # 科目时间优化代价
    subject_time_total_cost = sum(subject_time_costs)

    # 总体优化目标：最小化加权和
    model.Minimize(time_block_cost + subject_time_total_cost)
    # 求解
    solver = cp_model.CpSolver()

    # 使用的线程数
    # solver.parameters.num_search_workers = 1

    # 限制求解时间
    solver.parameters.max_time_in_seconds = 3600

    # 开启搜索进度
    solver.parameters.log_search_progress = True

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # 求解结果状态
        if status == cp_model.OPTIMAL:
            print("找到最优解")
        else:
            print("Feasible solution")

        # 求解结果
        df_dict = {}

        # 创建星期和课时
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六"]
        periods = ["第一节", "第二节", "第三节", "第四节", "第五节", "第六节", "第七节", "第八节", "第九节",]

        # 为每个班级创建一个 df
        for class_ in class_list:
            df_dict[class_] = pd.DataFrame(index=periods, columns=weekdays)

        # 解析结果
        for teacher in teacher_list:
            for class_ in class_list:
                for day in range(6):
                    for period in range(9):
                        for subject in subject_list:
                            if (solver.Value(x[teacher, class_, day, period, subject]) == 1):
                                df_dict[class_].loc[periods[period], weekdays[day]] = f"{subject}（{teacher}）"

        # 处理结果，每个 df 一个 sheet
        with pd.ExcelWriter("排课结果.xlsx") as writer:
            # 将每个DataFrame写入不同的sheet
            for class_, df in df_dict.items():
                df.to_excel(writer, sheet_name=class_)

    else:
        print("No optimal solution found.")