import pandas as pd

from TimeTable import plan

# 课时安排
data = pd.read_excel('./resources/data.xlsx', sheet_name="课时设置", header=1, index_col=0)

subject_title_list = list(data.columns)
subject_title_list = [item for item in subject_title_list if not item.startswith('课时')]

teacher_subjects = {}
for index, row in data.iterrows():
    for subject in subject_title_list:
        if pd.isna(row[subject]):
            continue
        if row[subject] in teacher_subjects:
            teacher_subject = teacher_subjects[row[subject]]
            if subject not in teacher_subject:
                teacher_subject.append(subject)
        else:
            teacher_subjects[row[subject]] = [subject]

subjects_required = {}
for index, row in data.iterrows():
    current_index_required = {}
    for subject in subject_title_list:
        if pd.isna(row[subject]):
            continue
        subject_column_index = data.columns.get_loc(subject)
        count = data.iloc[data.index.get_loc(index), subject_column_index + 1]
        current_index_required[subject] = int(count)
    subjects_required[index] = current_index_required

teacher_required = {}
for index, row in data.iterrows():
    current_index_required = {}
    for subject in subject_title_list:
        if pd.isna(row[subject]):
            continue
        teacher = row[subject]
        current_index_required[subject] = teacher
    teacher_required[index] = current_index_required

grade_teacher = {}
for index, row in data.iterrows():
    current_grade_teacher = []
    for subject in subject_title_list:
        if pd.isna(row[subject]):
            continue
        teacher = row[subject]
        if teacher not in current_grade_teacher:
            current_grade_teacher.append(teacher)
    grade_teacher[index] = current_grade_teacher

# 求解
plan(teacher_subjects, subjects_required, teacher_required)
