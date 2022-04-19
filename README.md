# Grade Calculator
What grade do I need to pass the course?

## Dependencies

This program requires Termcolor. To install it, run `pip install termcolor`.
## Basic Usage
```
python whatsmygrade.py [input file] [-args]
```
### Arguments
- `--no-color`: disable terminal coloring

### Input File
The `[input file]` is a path to a text file that defines the grade breakdown of your course, as well as what grades you currently have. An example of a file would look like this:
```python
# Grade file for MAT532
# you can write comments on any line prefixed by a "#"

[breakdown]
# these values represent WEIGHTS; they can, but do not need to, add up to 100%
# keep in mind, that "35%" is different from "35". "35" indicates "3500%".
final: 35%
midterm 1: 20%
midterm 2: 20%
homework: 25%

[grades]
# this is where you should enter your grades
# if you enter "unknown", then the program will compute your minimum value for the unknown grades such that you pass the course.
final: unknown
# values may also be Python-like expressions
midterm 1: 27/40
midterm 2: 86.2%
# if you have multiple grades for a category, you can use the grade_multiple function to compute them all at once
# in this case, we have 7 homework assignments, with grades 8/10, 6/10, 7/10, and so on.
# optionally, the argument drop_worst can be passed to drop a given number of worst grades

homework: grade_multiple([8, 6, 7, 9, 10, 7, 10], out_of=10, drop_worst=1)
[config]
# this section is optional; it allows you to specify information such as the course passing grade
passing_grade: 50%
```
