""" Scripts of tool."""
import argparse
import itertools
import os
import re
import six
import subprocess
import sys
import tempfile

from .base import OrderedField, DataDescription, Field
from .files import FileList
from .awk import AWKStreamProgram, AWKGroupProgram


def cat():
    """ cat function.

    tact file1, file2

    """
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Concatenate files and print on the standard output"
    )
    parser.add_argument(
        'files', metavar='FILE', type=argparse.FileType('r'), nargs="*")
    args = parser.parse_args()
    files = FileList(args.files)
    sys.stdout.write(files.header + '\n')
    sys.stdout.flush()
    files("cat")


def ttail():
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Tail files and print on the standard output"
    )
    parser.add_argument(
        'files', metavar='FILE', type=argparse.FileType('r'), nargs="*")
    parser.add_argument('-n', '--lines', default=10)
    args = parser.parse_args()
    files = FileList(args.files)
    sys.stdout.write(files.header + '\n')
    sys.stdout.flush()
    command = "tail" + " -n{}".format(args.lines) if args.lines else ""
    files(command)


def srt():
    """ sort function.

    tsrt -k field1 -k field2 file1

    """
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Sort lines of text files"
    )
    parser.add_argument(
        'files', metavar='FILE', type=argparse.FileType('r'), nargs="*")
    parser.add_argument('-k', '--keys', action="append", default=[])
    args = parser.parse_args()
    files = FileList(args.files)
    fields = [f.title for f in files.description.fields]
    order = [OrderedField.parse(key) for key in args.keys]
    options = [
        "-k{0},{0}{1}{2}".format(
            fields.index(f.title) + 1, f.sort_type, f.sort_order)
        for f in order
    ]
    sys.stdout.write(files.header + '\n')
    sys.stdout.flush()
    files("sort", *options)


def awk():
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Perform a map operation on all FILE(s)"
        "and write result to standard output."
    )
    parser.add_argument(
        'files', metavar='FILE', type=argparse.FileType('r'), nargs="*")
    parser.add_argument('-o', '--output', action="append",
                        help="Output fields", default=[])
    parser.add_argument('-f', '--filter', action="append", default=[],
                        help="Filter expression")
    parser.add_argument('--debug', action='store_true', default=False,
                        help="Print result program")
    args = parser.parse_args()
    files = FileList(args.files)
    program = AWKStreamProgram(
        files.description.fields,
        filters=args.filter,
        output_expressions=args.output
    )

    if args.debug:
        sys.stdout.write("%s\n" % program)

    description = DataDescription([
        Field(o.title, o._type) for o in program.output
        if o.title and not o.title.startswith('_')
    ])
    sys.stdout.write(str(description) + '\n')
    sys.stdout.flush()
    files('awk', '-F', '"\t"', '-v', 'OFS="\t"', str(program))


def grp():
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Perform a group operation on all FILE(s)"
        "and write result to standard output."
    )
    parser.add_argument(
        'files', metavar='FILE', type=argparse.FileType('r'), nargs="*")
    parser.add_argument('-k', '--groupkey', help="Group expression")
    parser.add_argument('-g', '--groupexpressions', action="append",
                        default=[], help="Group expression")
    parser.add_argument('--debug', action='store_true', default=False,
                        help="Print result program")
    args = parser.parse_args()
    files = FileList(args.files)

    program = AWKGroupProgram(
        files.description.fields,
        group_key=args.groupkey,
        group_expressions=args.groupexpressions
    )

    if args.debug:
        sys.stdout.write("%s\n" % program)

    description = DataDescription([
        Field(o.title, o._type) for o in program.key + program.output
        if o.title and not o.title.startswith('_')
    ])

    sys.stdout.write(str(description) + '\n')
    sys.stdout.flush()
    files('awk', '-F', '"\t"', '-v', 'OFS="\t"', str(program))


def pretty():
    """ Prettify output.

    Uses sys.stdin only
    tcat file | tpretty

    """
    header = sys.stdin.readline()
    fields = DataDescription.parse(header).fields
    column_widths = [len(str(field)) for field in fields]

    file_name = tempfile.mkstemp()[1]
    with open(file_name, 'w') as f:
        for line in sys.stdin:
            for findex, field in enumerate(line.rstrip('\n').split()):
                column_widths[findex] = max(column_widths[findex], len(field))
            f.write(line)

    column_widths = [x + 2 for x in column_widths]
    print("|".join([
        (" {} ".format(str(_f))).ljust(x)
        for x, _f in itertools.izip(column_widths, fields)
    ]))
    print("+".join(["-" * x for x in column_widths]))
    with open(file_name, 'r') as f:
        for line in f:
            print("|".join([
                (" {} ".format(str(field or ''))).ljust(x)
                for x, field in six.moves.zip_longest(
                    column_widths, line.rstrip('\n').split()
                )
            ]))
    os.remove(file_name)


def plot():
    """ Use gnuplot with tab files.

    Usage
    -----
    cat file.tsv | tplot -e '<optional command>' script.gnu

    Input file should have name: '__input'
    Fields should start with: '__', for example instead of a use __a.

    Examples
    --------

    cat data.tsv | tplot -c script.gnu  -e "set output 'output2.png'"
    cat data.tsv | tplot -c script.gnu > ouput3.png

    """
    parser = argparse.ArgumentParser(
        add_help=True,
        description="Plot file from stdin with gnuplot"
    )
    parser.add_argument('-c', '--gnuplot-script', required=True,
                        help="file with gnuplot commangs")
    parser.add_argument('-e', '--gnuplot-commands',
                        help="command1; command2; ...")
    parser.add_argument('--debug', action='store_true', default=False,
                        help="Print result program")

    args = parser.parse_args()
    header = sys.stdin.readline()
    fields = DataDescription.parse(header).fields
    file_name = tempfile.mkstemp()[1]

    # Write data file to temporary location without header.
    # NOTE: gnuplot draw from standard input feature could not be used because
    # file mith be used several times (subplots)
    with open(file_name, 'w') as f:
        for line in sys.stdin:
            f.write(line)

    script_file_name = tempfile.mkstemp()[1]

    substitutors = [
        (index, re.compile("__" + title)) for title, index in sorted([
            (field.title, index) for index, field in enumerate(fields)
        ], reverse=True)
    ]
    with open(script_file_name, 'w') as f:
        with open(args.gnuplot_script) as source:
            for line in source:
                line = re.sub('__input', file_name, line)
                for index, substitutor in substitutors:
                    line = substitutor.sub(str(index + 1), line)

                f.write(line)

    command = 'gnuplot{} -c {}'.format(
        ' -e "{}"'.format(args.gnuplot_commands)
        if args.gnuplot_commands else '',
        script_file_name)

    if args.debug:
        sys.stdout.write("%s\n" % command)
        with open(script_file_name) as f:
            sys.stdout.write(f.read())

    subprocess.call(command, shell=True)
    os.remove(script_file_name)
    os.remove(file_name)
