grade_options = {"v_grade": ["", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"],
                 "font": ["", "5a", "5b", "5c", "6a", "6a+", "6b", "6c", "6c+", "7a", "7a+"]}
grade_system_choices = (("v_grade", "V System"), ("font", "Font System"))

counter = 0
all_grade_choices = []
for _, grade_list in grade_options.items():
    for i, item in enumerate(grade_list):
        all_grade_choices.append((str(counter + i), item))
    counter += len(grade_list)

ALLOWED_EXTENSIONS = {'png'}