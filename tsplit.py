#!/usr/bin/env python3
"""
Takes a list of tasks, and outputs them in a format that todoist can read.
"""
import re
import argparse
from datetime import datetime, date, timedelta
import math
import pathlib

import pandas as pd


parser = argparse.ArgumentParser(
    description="Takes a list of tasks to do, and generates a list of todoist tasks and gantt chart tasks in a csv file which can easily be uploaded to a gantt app or todoist.\nNote, expects topics to be separated by a special character: –"
)

parser.add_argument(
    "-p",
    "--path",
    default="tasks.txt",
    help="path of the text file containing list of tasks (default: tasks.txt)",
)
parser.add_argument(
    "-s",
    "--start",
    default=date.today().isoformat(),
    help="The day from which you want to start scheduling the tasks, in ISO format (YYYY-MM-DD) (default: today)",
)
parser.add_argument(
    "-e",
    "--end",
    default="",
    help="Day after the last day you want tasks to be scheduled for, in ISO format (YYYY-MM-DD), required if not segmenting tasks.",
)
parser.add_argument(
    "-i",
    "--interval",
    default=None,
    help="Schedules tasks with a specified interval of days between them, instead of based on an end date. Note using this option means the value for -e is ignored.",
)
parser.add_argument(
    "-f",
    "--fit",
    action="store_true",
    help="Moves the end date back such that you have the exact same number of tasks per day (default: false)",
)
parser.add_argument(
    "-o", "--output", help="output directory (default: current directory)", default=""
)
parser.add_argument(
    "-n",
    "--name",
    help="prefix for output files (default: name of the file containing tasks)",
    default=None,
)
parser.add_argument(
    "-ut",
    "--unit-title",
    help="adds unit title prefix for portions",
    action=argparse.BooleanOptionalAction,
    default=False,
)
parser.add_argument(
    "-un",
    "--unit-number",
    help="adds unit number prefix for portions",
    action=argparse.BooleanOptionalAction,
    default=True,
)
parser.add_argument(
    "-st",
    "--subject-title",
    help="adds subject title prefix for portions",
    action=argparse.BooleanOptionalAction,
    default=True,
)
parser.add_argument(
    "-r",
    "--priority",
    default="2",
    help="the priority of the task in todist (default: 2)",
)
parser.add_argument(
    "-m",
    "--mode",
    choices=["s", "single", "m", "multi", "multiple"],
    help="whether it should treat the input as a single list, or multiple lists each separated by a blank line.",
    required=True,
)
# parser.add_argument(
#     "-sgt",
#     "--segment-time",
#     help="Allows you to specify a time segment for some tasks",
#     action=argparse.BooleanOptionalAction,
#     default=True
# )
parser.add_argument(
    "-ss",
    "--set-segment",
    help="Allows you to set duration of segment for those tasks which don't have any, default behaviour is set them so that fills remaining time equally",
    default="-1",
)

# parser.add_argument("-md", "--max-denominator", help = "the maximum denominator when splitting tasks by day, default 12, set to 0 for no limit", default = 12)


def add_prefix(prefix, part):
    if prefix != "":
        prefix += "-"
    prefix += part
    return prefix


def combine_prefix(prefix, topic):
    return topic if prefix == "" else f"{prefix}: {topic}"


def parse_tasks(args, part):
    """
    First, if the user wants the title to prefix the task, reads the title, sets it as prefix
    Then, it tries and detects the format, and based on that parse and return a list of tasks.

    args: command line arguments
    part: An independent part of the input document, separated from other content by a blank line,
    can either be a list of tasks, or in portions format(see Ex1/Ex2 for details)

    returns: task_list, the list of tasks to convert to todoist/gannt form.
    """
    list_exp = r"^\s*(\d+\.\s*(?:(?!\n\d+\.).)*)"
    portions_unit_heading_exp = r"^UNIT\s+(?P<unit_number>[^\s]*)\s+(?P<unit_name>.*)\s*"  # Single Line Regex which matches a Unit Number and Name Alone
    task_list = []

    prefix = ""

    subject_title_exp = r"^\s*title:\s*(.*)\n"
    if args.subject_title and (
        subject_title_matches := re.findall(
            subject_title_exp, part, flags=re.MULTILINE | re.IGNORECASE
        )
    ):
        subject_title = subject_title_matches[0]
        prefix = add_prefix(prefix, subject_title)
        part = re.sub(subject_title_exp, r"", part)

    part = part.strip()

    if re.search(list_exp, part, flags=re.MULTILINE):  # List of tasks in form
        # 1. ...
        # 2. ...
        # etc.
        task_list = re.findall(list_exp, part, flags=re.MULTILINE)
        # print(task_list)
        task_list = [combine_prefix(prefix, topic) for topic in task_list]
        # print(task_list)
    elif re.search(portions_unit_heading_exp, part):  # In portions format
        task_list = parse_portions(args, part, portions_unit_heading_exp, prefix)
    else:  # As a normal list
        topics = part.split("\n")

        task_list = [
            combine_prefix(prefix, topic) for topic in topics
        ]  # we can't do this at the end for all of these, as the prefix changes from chapter to chapter.

    return task_list


def parse_portions(
    args,
    part,
    portions_unit_heading_exp,
    prefix,
):
    """
    parses part according to the portions format, returns a list of tasks = topics + prefix

    portions_unit_heading_exp: The regular expression used to a)detect if the part is in portions format, and
    b) split the part into units, parse the unit to get the unit number, and the unit content.

    prefix: The string to prepend to every 'topic' (topic in portions without subject title or unit title/number) to convert it to a task(a topic with the extra info mentioned before prepended)
    """

    """
    Suggestion for improving parsing so context given for tasks:
    For portions, first we apply:
    First apply:
    a - b, c, d -> a: b - c - d;
    then:
    a, b, c- -> a - b - c
    then:
    a: b - c: d - e -> a:b - a:c:d - a:c:e, terminates with ; or .
    then:
    split on "-"
    """

    task_list = []
    if part.count(",") > part.count(
        " – "
    ):  # We know it is a special case, like understanding harmony syntax.
        part = part.replace("–", ":")

    units = re.split(portions_unit_heading_exp, part, flags=re.MULTILINE)[
        1:
    ]  # Matches unit heading, splits the part into constituent units. re.split output is in format [(content matched by capture group in split regex 1), (content matched by capture group in split regex 2), ... (actual data between split regex), ...(repeats)]
    units[-1] = re.sub(
        r"^TOTAL PERIODS:.*$", r"", units[-1], flags=re.MULTILINE
    )  # The end of every part containing portions will have 'Total Number of Periods' Line we don't want: (see example), so we just replace that with "" to remove it.

    for unit_number, unit_title, unit_content in zip(
        units[::3], units[1::3], units[2::3]
    ):
        new_prefix = prefix
        # TERMINATORS = [";", ".", "$"]
        unit_content = unit_content.replace("\n", " ")

        # if args.other_mode:
        #     TERMINATORS_1 = TERMINATORS + [","]
        #     HEADER = r"([^–,;]+)"
        #     SUBTOPICS = r"((?:[^,–;]+,)*)"
        #     END = r"([^,–;]+)(?:,|;|\.|$)"
        #     find1 = rf"{HEADER}–{SUBTOPICS}{END}"
        #     find1 matches all occurence of a - b, c, d..., it was going to be used to add more context, but I gave up because I thought it would take too much time.
        #     matches = re.sub(find1, replace_func)

        #
        unit_content = unit_content.replace(";", " – ").replace(",", " – ")
        topics = re.split(r"\s–\s", unit_content)

        if args.unit_number:
            new_prefix = add_prefix(prefix, unit_number)
        if args.unit_title:
            new_prefix = add_prefix(prefix, unit_title)

        mini_task_list = [combine_prefix(new_prefix, topic) for topic in topics]

        task_list.extend(mini_task_list)
    return task_list


def start_end_days(args, num_tasks):
    start = date.fromisoformat(args.start)
    if not args.interval:
        end = date.fromisoformat(args.end)
    else:
        end = start + timedelta(days=num_tasks * float(args.interval))

    date_diff = end - start
    days = date_diff.days
    days_per_task = days / num_tasks
    tasks_per_day = num_tasks / days

    return start, end, days, days_per_task, tasks_per_day


def td_split_rows(g_rows):
    rows = []
    for task in g_rows:
        name, start, end = task
        days = max(1, (end - start).days)
        rows.extend(
            [
                [f"{name} ({day+1}/{days})", start + timedelta(days=day)]
                for day in range(days)
            ]
        )
    # num_tasks = len(task_list)
    # start, _, days, days_per_task, _ = start_end_days(args, num_tasks)
    # rows = []
    # num, denom = num_tasks, days
    # args.max_denominator = max(args.max_denominator, math.ceil(days_per_task))
    # if(args.fit):
    #     num = 1
    #     denom = int(days_per_task)
    # else:
    #     gcd = math.gcd(num, denom)
    #     num, denom = num // gcd, denom // gcd

    # for cur, i in zip(range(num, num*(days+1), num), range(days)):
    #     task_index = cur // denom - 1 if cur % denom == 0 else cur // denom
    #     if(task_index >= len(task_list)):
    #         break
    #     task_num = cur - task_index * denom
    #     completion_frac = Fraction(task_num, denom).limit_denominator(args.max_denominator)

    #     task_name = f"{task_list[task_index]} ({completion_frac.numerator}/{completion_frac.denominator})"
    #     rows.append([task_name, start + timedelta(days = i)])

    return rows


def gantt_rows(args, task_list):
    start, _, days, days_per_task, _ = start_end_days(args, len(task_list))
    if args.fit:
        days_per_task = int(days_per_task)

    rows = [
        [
            task_list[i],
            start + timedelta(days=int(days_per_task * i)),
            start + timedelta(days=int(days_per_task * (i + 1))),
        ]
        for i in range(len(task_list))
    ]
    return rows


def to_todoist(df: pd.DataFrame, priority: str):
    #print(df)
    df = df.rename({"NAME": "CONTENT", "START": "DATE"}, axis=1)
    df["TYPE"] = "task"
    df["DATE_LANG"] = "en"
    df["PRIORITY"] = priority
    df["DESCRIPTION"] = df["INDENT"] = df["AUTHOR"] = df["RESPONSIBLE"] = df[
        "TIMEZONE"
    ] = ""
    new = df[
        [
            "TYPE",
            "CONTENT",
            "DESCRIPTION",
            "PRIORITY",
            "INDENT",
            "AUTHOR",
            "RESPONSIBLE",
            "DATE",
            "DATE_LANG",
            "TIMEZONE",
        ]
    ]
    return new


def td_inter_rows(args, gantt: pd.DataFrame):
    tot_tasks = len(gantt)
    rows = []
    start, _, _, _, tasks_per_day = start_end_days(args, tot_tasks)
    if args.fit:
        tasks_per_day = math.ceil(tasks_per_day)

    gantt = gantt.sort_values("END", ascending=True, kind="stable")

    added_tasks = 0
    done_tasks = 0
    i = 0
    while added_tasks < len(gantt):
        done_tasks += tasks_per_day
        done_tasks = min(
            done_tasks, len(gantt)
        )  # Make sure that done_tasks doesn't become greater than total no. tasks due to floating point error.
        # print(f"{done_tasks=}")
        while added_tasks < done_tasks:
            # print(f"{added_tasks=}")
            rows.append([gantt.iloc[added_tasks].NAME, start + timedelta(days=i)])
            added_tasks += 1
        i += 1

    td_inter_rows = pd.DataFrame(rows, columns=["NAME", "START"])
    return td_inter_rows


def get_dfs(args, text):
    parts = [text]
    if "m" in args.mode:
        parts = text.split("\n\n")

    task_lists = [parse_tasks(args, part) for part in parts]

    with open("log.txt", "a", encoding="utf-8") as f:
        for task_list in task_lists:
            f.write(str(task_list))
            f.write("\n\n")
        # f.write(str(task_lists))

    td_split, td_inter, gantt = [], [], []
    for task_list in task_lists:
        g_rows = gantt_rows(
            args, task_list
        )  # Gannt basically does the timing calculation, the rest just convert from gannt to the desired format.
        td_split.extend(td_split_rows(g_rows))
        gantt.extend(g_rows)
    td_split = pd.DataFrame(td_split, columns=["NAME", "START"])
    gantt = pd.DataFrame(gantt, columns=["NAME", "START", "END"])
    # gantt = gantt.sort_values("START", axis=0, ignore_index=True, kind="stable") # Uncomment this if you want sorted before inter rows, this tends to jumble up the tasks from different subjects more, while not having it tends to group tasks from the same subject together.

    td_inter = td_inter_rows(args, gantt)

    td_split = td_split.sort_values("START", axis=0, ignore_index=True, kind="stable")

    gantt = gantt.sort_values("START", axis=0, ignore_index=True, kind="stable")

    td_inter = td_inter.sort_values("START", axis=0, ignore_index=True, kind="stable")
    return gantt, td_split, td_inter


def main():
    args = parser.parse_args()
    test_path = pathlib.Path(args.path)
    if not test_path.exists():
        parser.error(
            "The path provided to --path does not exist! (If no path was provided, then 'tasks.txt' was assumed to be the path)"
        )

    with open(args.path, "r", encoding="utf-8") as f:
        text = f.read()
    
    #print(text)
    text = re.sub(r'#[^\n]*\n', "", text)
    segs = re.split(r"s\(([^)]*)\):", text)
    # print(len(segs))
    if len(segs) > 1:
        segs = segs[1:]
        seg_end_pairs = [[text, end] for text, end in zip(segs[1::2], segs[::2])]
        seg_end_pairs[-1][1] = (
            args.end if args.end.strip() != "" else seg_end_pairs[-1][1]
        )
    else:
        seg_end_pairs = [[segs[0], args.end]]

    cur_datetime = datetime.fromisoformat(args.start)

    increment = (
        timedelta(days=int(args.set_segment)) if int(args.set_segment) > 0 else None
    )

    for i, pair in enumerate(seg_end_pairs):
        text, end = pair
        if end.strip().isdigit():
            cur_datetime += timedelta(days=int(end))
            pair[1] = (cur_datetime + timedelta(days=int(end))).date().isoformat()
        elif end.strip() == "":
            if increment is None and args.end.strip() == "":
                raise ValueError(
                    "You haven't providided an end date, and no end date/days for the tasks/segment of tasks, or a default number of days. Please Provide one of these"
                )
            increment = (
                (datetime.fromisoformat(args.end) - cur_datetime)
                / (len(seg_end_pairs) - i)
                if increment is None
                else increment
            )
            cur_datetime += increment
            pair[1] = cur_datetime.date().isoformat()
        else:
            cur_datetime = datetime.fromisoformat(end)

    gantt, td_split, td_inter = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    #print(seg_end_pairs)
    for text, end in seg_end_pairs:
        args.end = end
        g, s, i = get_dfs(args, text)
        args.start = args.end
        gantt = pd.concat([gantt, g], ignore_index=True)
        td_split = pd.concat([td_split, s], ignore_index=True)
        td_inter = pd.concat([td_inter, i], ignore_index=True)

    if args.name is None:
        args.name = args.path
        if "." in args.name:
            args.name = args.name[: args.name.index(".")]

    if args.output != "" and not args.output[-1] == "/":
        args.output += "/"

    init_path = f"{args.output}{args.name}_"

    td_split = to_todoist(td_split, args.priority)

    td_inter = to_todoist(td_inter, args.priority)

    gantt.to_csv(init_path + "gantt.csv", index=False)

    td_split.to_csv(init_path + "td_split.csv", index=False)

    td_inter.to_csv(init_path + "td_inter_rows.csv", index=False)
    # print(seg_end_pairs)


main()


# parts_lines = []
# for part in parts:
#     if "-" in part:
#         re.sub(par)
# parts_lines = [part.split("\n") for part in parts]


# def excel_output(part:str):
#     part.

# path = input("Enter path: ")
# if path == "":
#     path = "tasks.txt"
