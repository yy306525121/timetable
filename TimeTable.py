import math

from ortools.sat.python import cp_model
import pandas as pd

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


    # 约束条件：每个老师只能给固定的班级授课
    for teacher in teacher_list:
        for class_ in class_list:
            for subject in subject_list:
                if teacher_required.get(class_, {}).get(subject) == teacher:
                    model.Add(
                        sum(
                            x[teacher, class_, day, period, subject]
                            for day in range(6)
                            for period in range(9)
                        )>= 1
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
                    model.add(lesson_count >= 1)
                    model.add(lesson_count <= 2)
                else:
                    model.add(lesson_count <= 1)

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

    # 第一个目标:课程靠前的权重系数
    alpha = 1.0

    # 第二个目标:课程集中的权重系数
    beta = 2.0  # beta的值可以根据实际需求调整,值越大表示越重视课程集中
    # 约束条件，周1、3、5语文尽量靠前，周2、4、6英语尽量靠前
    # 第一部分:课程靠前的目标
    objective_terms_1 = []
    for class_ in class_list:
        for day in range(6):
            if day % 2 == 0:
                teacher = teacher_required.get(class_, {}).get('语文')
                for period in range(9):
                    objective_terms_1.append(x[teacher, class_, day, period, '语文'] * period)
            else:
                teacher = teacher_required.get(class_, {}).get('英语')
                for period in range(9):
                    objective_terms_1.append(x[teacher, class_, day, period, '英语'] * period)

    # 第二部分:课程集中的目标
    span = {}
    for teacher in teacher_list:
        for day in range(6):
            # 判断这天是否有课
            has_class = model.NewBoolVar(f'has_class[{teacher},{day}]')
            model.Add(sum(x[teacher, class_, day, period, subject]
                          for class_ in class_list
                          for period in range(9)
                          for subject in subject_list) >= 1).OnlyEnforceIf(has_class)

            max_period = model.NewIntVar(0, 8, f'max_period[{teacher},{day}]')
            min_period = model.NewIntVar(0, 8, f'min_period[{teacher},{day}]')

            for period in range(9):
                for class_ in class_list:
                    for subject in subject_list:
                        b = x[teacher, class_, day, period, subject]
                        model.Add(max_period >= period).OnlyEnforceIf(b)
                        model.Add(min_period <= period).OnlyEnforceIf(b)

            span[teacher, day] = model.NewIntVar(0, 8, f'span[{teacher},{day}]')
            model.Add(span[teacher, day] == max_period - min_period).OnlyEnforceIf(has_class)
            model.Add(span[teacher, day] == 0).OnlyEnforceIf(has_class.Not())

    objective_terms_2 = [span[teacher, day] for teacher in teacher_list for day in range(6)]

    # 组合两个目标
    model.Minimize(alpha * sum(objective_terms_1) + beta * sum(objective_terms_2))

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