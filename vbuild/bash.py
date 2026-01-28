# Based on https://github.com/toltec-dev/build/blob/main/toltec/bash.py

import os
import shlex
import subprocess

from io import StringIO
from typing import cast

AssociativeArray = dict[str, str]
IndexedArray = list[str | None]
VariableValue = AssociativeArray | IndexedArray | str | None
Variables = dict[str, VariableValue]
Functions = dict[str, str]

DEFAULT_VARIABLE_NAMES = {
    # Defaults from https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html
    "_",
    "BASH",
    "BASHOPTS",
    "BASHPID",
    "BASH_ALIASES",
    "BASH_ARGC",
    "BASH_ARGV",
    "BASH_ARGV0",
    "BASH_CMDS",
    "BASH_COMMAND",
    "BASH_COMPAT",
    "BASH_ENV",
    "BASH_EXECUTION_STRING",
    "BASH_LINENO",
    "BASH_LOADABLES_PATH",
    "BASH_MONOSECONDS",
    "BASH_REMATCH",
    "BASH_SOURCE",
    "BASH_SUBSHELL",
    "BASH_TRAPSIG",
    "BASH_VERSINFO",
    "BASH_VERSION",
    "BASH_XTRACEFD",
    "CHILD_MAX",
    "COLUMNS",
    "COMP_CWORD",
    "COMP_KEY",
    "COMP_LINE",
    "COMP_POINT",
    "COMP_TYPE",
    "COMP_WORDBREAKS",
    "COMP_WORDS",
    "COMPREPLY",
    "COPROC",
    "DIRSTACK",
    "EMACS",
    "ENV",
    "EPOCHREALTIME",
    "EPOCHSECONDS",
    "EUID",
    "EXECIGNORE",
    "FCEDIT",
    "FIGNORE",
    "FUNCNAME",
    "FUNCNEST",
    "GLOBIGNORE",
    "GLOBSORT",
    "GROUPS",
    "histchars",
    "HISTCMD",
    "HISTCONTROL",
    "HISTFILE",
    "HISTFILESIZE",
    "HISTIGNORE",
    "HISTSIZE",
    "HISTTIMEFORMAT",
    "HOSTFILE",
    "HOSTNAME",
    "HOSTTYPE",
    "IGNOREEOF",
    "INPUTRC",
    "INSIDE_EMACS",
    "LANG",
    "LC_ALL",
    "LC_COLLATE",
    "LC_CTYPE",
    "LC_MESSAGES",
    "LC_NUMERIC",
    "LC_TIME",
    "LINENO",
    "LINES",
    "MACHTYPE",
    "MAILCHECK",
    "MAPFILE",
    "OLDPWD",
    "OPTERR",
    "OSTYPE",
    "PIPESTATUS",
    "POSIXLY_CORRECT",
    "PPID",
    "PROMPT_COMMAND",
    "PROMPT_DIRTRIM",
    "PS0",
    "PS3",
    "PS4",
    "PWD",
    "RANDOM",
    "READLINE_ARGUMENT",
    "READLINE_LINE",
    "READLINE_MARK",
    "READLINE_POINT",
    "REPLY",
    "SECONDS",
    "SHELL",
    "SHELLOPTS",
    "SHLVL",
    "SRANDOM",
    "TIMEFORMAT",
    "TMOUT",
    "TMPDIR",
    "UID",
    # Variables that are almost always set
    "IFS",
    "PATH",
    "OPTIND",
    "TERM",
}


class BashSyntaxError(Exception):
    def __init__(self, msg: str, file: str, lineno: int) -> None:
        super().__init__(f"{file}:L{lineno}: {msg}")


def run_bash(src: str) -> str:
    env = {"PATH": os.environ["PATH"]}
    process = subprocess.run(["bash"], input=src.encode(), capture_output=True, env=env)
    errors = process.stderr.decode()
    if process.returncode == 2 or "syntax error" in errors:
        raise BashSyntaxError(errors, src, 0)

    if process.returncode != 0 or errors:
        raise subprocess.CalledProcessError(
            process.returncode, "bash", process.stdout, errors
        )

    return process.stdout.decode()


def assert_token(lexer: shlex.shlex, value: str) -> str:
    token = lexer.get_token()
    assert token == value
    return token or ""


def parse(src: str) -> tuple[Variables, Functions]:
    declarations = run_bash(src + "\n declare -f\n declare -p")
    lexer = shlex.shlex(declarations, posix=True)
    lexer.wordchars = lexer.wordchars + "-"
    variables: Variables = {}
    functions: Functions = {}
    while True:
        token = lexer.get_token()
        if token == lexer.eof:
            break

        assert token is not None
        next_token = lexer.get_token()
        assert next_token is not None

        if token == "declare" and next_token[0] == "-":
            lexer.push_token(next_token)
            name, value = parse_variable(lexer)
            variables[name] = value
            continue

        if next_token != "(":
            raise BashSyntaxError(
                f"Unexpected token: '{next_token}'. Expecting '('", src, lexer.lineno
            )

        following_token = lexer.get_token()
        if following_token != ")":
            raise BashSyntaxError(
                f"Unexpected token: '{next_token}'. Expecting ')'", src, lexer.lineno
            )

        start, end = parse_function(lexer)
        functions[token] = declarations[start:end].strip(" ")

    return variables, functions


def parse_function(lexer: shlex.shlex) -> tuple[int, int]:
    _ = assert_token(lexer, "{")
    assert lexer.instream is not None
    stream = cast(StringIO, lexer.instream)
    start = stream.tell()

    depth = 1
    while depth > 0:
        token = lexer.get_token()
        assert token != lexer.eof
        match token:
            case "{":
                depth += 1

            case "}":
                depth -= 1

            case _:
                pass

    end = stream.tell() - 1
    return start, end


def get_string(lexer: shlex.shlex) -> str:
    string_token = lexer.get_token() or ""
    if string_token == "$":
        quoted_string = lexer.get_token() or ""
        string_token = run_bash("echo -n $" + shlex.quote(quoted_string))

    return parse_string(string_token)


def parse_variable(lexer: shlex.shlex) -> tuple[str, VariableValue]:
    flags_token = lexer.get_token()
    assert flags_token is not None
    flags: set[str] = set(flags_token[1:]) if flags_token != "--" else set()
    name = lexer.get_token()
    assert name is not None
    value: VariableValue = None
    next_token = lexer.get_token()
    assert next_token is not None
    if next_token != "=":
        lexer.push_token(next_token)
        return name, value

    if "a" in flags:
        value = parse_indexed(lexer)
        return name, value

    if "A" in flags:
        value = parse_associative(lexer)
        return name, value

    value = get_string(lexer)
    return name, value


def parse_string(token: str) -> str:
    return token.replace("\\$", "$")


def parse_indexed(lexer: shlex.shlex) -> IndexedArray:
    _ = assert_token(lexer, "(")
    data: IndexedArray = []
    while True:
        token = lexer.get_token()
        assert token != lexer.eof
        if token == ")":
            break

        assert token == "["
        index = int(lexer.get_token() or "")
        _ = assert_token(lexer, "]")
        _ = assert_token(lexer, "=")
        value = get_string(lexer)
        if index >= len(data):
            data.extend([None] * (index - len(data) + 1))

        data[index] = value

    return data


def parse_associative(lexer: shlex.shlex) -> AssociativeArray:
    _ = assert_token(lexer, "(")
    data: AssociativeArray = {}
    while True:
        token = lexer.get_token()
        assert token != lexer.eof
        if token == ")":
            break

        assert token == "["
        key = lexer.get_token()
        assert key is not None
        _ = assert_token(lexer, "]")
        _ = assert_token(lexer, "=")
        value = get_string(lexer)
        data[key] = value

    return data
