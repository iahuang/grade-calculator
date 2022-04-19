import sys
import os
import re
from dataclasses import dataclass
from typing import Any, Optional, Union, cast
from termcolor import colored as _colored

# helper functions


def helper_grade_parts(*args: tuple[float, float]) -> float:
    total_points = sum(arg[1] for arg in args)
    points_earned = sum(arg[0] for arg in args)
    return points_earned / total_points


def helper_grade_multiple(grades: list[float], out_of: float, use_best: Optional[int] = None, drop_worst: Optional[int] = None) -> float:
    grades = sorted(grades, reverse=True)
    if use_best:
        grades = grades[:use_best]
    if drop_worst:
        grades = grades[:len(grades) - drop_worst]
    if len(grades) == 0:
        return 0.0
    return sum(grades) / (out_of * len(grades))


def helper_percent(n: float) -> float:
    return n / 100


class Config:
    use_color = True


def colored(msg: Any, color: str) -> str:
    msg = str(msg)

    if Config.use_color:
        return _colored(msg, color)
    else:
        return msg


class UserError(Exception):
    offending_line: Optional[str]
    msg: str

    def __init__(self, msg: str, offending_line: Optional[str] = None):
        super().__init__(msg)

        self.msg = msg
        self.offending_line = offending_line


def weighted_average(data: list[tuple[float, float]]) -> float:
    """
    Return a weighted average for data, where each element of data takes the form
    (value, weight)
    """
    if len(data) == 0:
        return 0.0

    sum_weights = sum(part[1] for part in data)
    weighted_total = sum(part[0] * part[1] for part in data)
    return weighted_total/sum_weights


class GradingScheme:
    _scheme: dict[str, float]
    _name_order: list[str]

    def __init__(self, scheme: list[tuple[str, float]]):
        self._scheme = {
            name: weight for name, weight in scheme
        }
        self._name_order = [name for name, _ in scheme]

    def compute_grade(self, values: dict[str, float]) -> float:
        """
        Return a grade (where 100% is 1.0) for the values given
        in the context of this grading scheme.
        """

        data: list[tuple[float, float]] = []

        for name in self._scheme.keys():
            weight = self._scheme[name]
            value = values.get(name)
            if value is None:
                raise UserError('Missing grade entry for "{}"'.format(name))
            data.append((value, weight))

        return weighted_average(data)
    
    def get_min_value_for_unknown(self, unknowns: list[str], known_values: dict[str, float], passing: float) -> Optional[int]:
        for min_percent in range(0, 101):
            value = min_percent/100

            values = {k:v for k,v in known_values.items()}
            for u in unknowns:
                values[u] = value

            if self.compute_grade(values) > passing:
                return min_percent
        
        return None

    def get_categories(self) -> list[str]:
        return self._name_order[:]

    def get_weight(self, category_name: str) -> float:
        return self._scheme[category_name]
    
    def get_weight_proportional(self, category_name: str) -> float:
        return self._scheme[category_name] / sum(self._scheme.values())


class VariableGrade:
    pass


class GradeFileParser:
    grading_scheme: GradingScheme
    grades: list[tuple[str, Union[float, VariableGrade]]]
    passing_grade: float
    has_been_parsed: bool

    def __init__(self):
        # provide default values for this object's members
        # we won't be able to do anything anyway
        # until self.has_been_parsed is True.
        self.grading_scheme = GradingScheme([])
        self.grades = []
        self.passing_grade = 0.5

        self.has_been_parsed = False

    def eval_expr(self, expr: str) -> Union[float, VariableGrade]:
        unknown = VariableGrade()
        expr = expr.strip()
        try:
            if re.findall(r"^\d+(\.\d+)?%$", expr):
                # expr is a percentage
                return float(expr[:-1]) / 100
            return eval(expr, {}, {
                # add helper functions
                "grade_parts": helper_grade_parts,
                "grade_multiple": helper_grade_multiple,
                "percent": helper_percent,
                "unknown": unknown
            })
        except SyntaxError:
            raise UserError('Invalid expression "{}"'.format(expr))

    def _parse_file_content(self, content: str) -> None:
        lines = content.split("\n")

        mode: Optional[str] = None
        scheme: list[tuple[str, float]] = []

        for line in lines:
            line = line.strip()
            if line == "":
                continue
            if line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                mode = line[1:-1]
            else:
                # lines of the form "name: value" must be contextualized
                # by a mode, designated by "[mode_name]"
                if not mode:
                    raise UserError('Unexpected statement "{}"'.format(line))

                name_match = re.findall(r"^[\w\- ]+", line)
                if not name_match:
                    raise UserError("Missing value name", offending_line=line)

                value_name: str = name_match[0]
                # remove the value name from the start of the line
                assert line.startswith(value_name)
                line = line[len(value_name):]

                # there should be a colon at the new start of the line
                if not line.startswith(":"):
                    raise UserError("Expected colon", offending_line=line)
                line = line[1:]  # remove the colon

                # there should be an expression
                if line == "":
                    raise UserError(
                        "Expected expression following a colon", offending_line=line)

                value = self.eval_expr(line)

                # now, we do something with the value_name: value pair we just got
                if mode == "breakdown":
                    if isinstance(value, float) or isinstance(value, int):
                        scheme.append((value_name, value))
                    else:
                        raise UserError("Invalid weight", offending_line=line)

                if mode == "grades":
                    self.grades.append((value_name, value))
                
                if mode == "config":
                    if value_name == "passing_grade":
                        self.passing_grade = cast(float, value)
                    else:
                        raise UserError('Unknown config option "{}"'.format(value_name))

        # finish up
        self.grading_scheme = GradingScheme(scheme)

    def parse_file(self, path: str) -> None:
        if not os.path.exists(path):
            raise UserError('Cannot find file with path "{}"'.format(path))

        with open(path) as fl:
            self._parse_file_content(fl.read())

        self.has_been_parsed = True

    def grade_summary(self) -> None:
        print("===== GRADE SUMMARY =====")
        categories = self.grading_scheme.get_categories()
        grades = {category: value for category, value in self.grades}
        col_left = [
            colored(category_name, "cyan") + " ({}%)".format(
                round(self.grading_scheme.get_weight_proportional(category_name) * 100)
            )
            for category_name in categories
        ]
        col_right = []
        for category in categories:
            if category not in grades:
                col_right.append(colored("(unspecified)", "red"))
            else:
                value = grades[category]

                if isinstance(value, VariableGrade):
                    col_right.append(colored("unknown", "yellow"))
                else:
                    col_right.append(colored("{:.2f}%".format(value*100), "green" if value >= self.passing_grade else "red"))

        col_left_size = max(len(s) for s in col_left)+1

        for left, right in zip(col_left, col_right):
            print(left + ":" + (" "*(col_left_size - len(left))) + right)

        unknowns = [name for name, value in grades.items() if isinstance(value, VariableGrade)]
        knowns = {name:value for name, value in grades.items() if not isinstance(value, VariableGrade)}
        if len(unknowns) > 0:
            minimum_grade_percent = self.grading_scheme.get_min_value_for_unknown(unknowns, knowns, self.passing_grade)

            if minimum_grade_percent is not None:
                print("To pass the course with a {}, you would need, at minimum, a {} in {}.".format(
                    colored(str(self.passing_grade*100)+"%", "green"),
                    colored(str(minimum_grade_percent)+"%", "cyan"),
                    ", ".join(colored(u, "cyan") for u in unknowns)
                ))
            else:
                print("You would not be able the course with a {}, even with a perfect score (100) in {}.".format(
                    colored(str(self.passing_grade*100)+"%", "green"),
                    ", ".join(colored(u, "cyan") for u in unknowns)
                ))
        
        else:
            computed_score = self.grading_scheme.compute_grade(cast(Any, grades))
            print()
            print("===== OVERALL SCORE =====")
            print(colored(
                "          {:.2f}%         ".format(computed_score*100),
                "green" if computed_score > self.passing_grade else "red"
            ))
        
if __name__ == "__main__":
    args = sys.argv[1:]

    opts: list[str] = []
    input_files: list[str] = []

    for arg in args:
        if arg.startswith("--"):
            opts.append(arg)
        else:
            input_files.append(arg)

    Config.use_color = "--no-color" not in opts

    if len(input_files) == 0:
        print(colored("error: no input files", "red"))
        quit()

    if len(input_files) > 1:
        print(colored("error: too many input files", "red"))
        quit()

    input_file = input_files[0]

    try:
        parser = GradeFileParser()
        parser.parse_file(input_file)
        parser.grade_summary()
    except UserError as err:
        print(colored("error: "+err.msg, "red"))
        if err.offending_line:
            print(colored('at line: "{}"'.format(err.offending_line), "red"))
