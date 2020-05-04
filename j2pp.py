#!/usr/bin/env python3

import argparse
import asyncio as a
import datetime
import difflib
import errno
import functools as f
import importlib.util
import inspect
import itertools as i
import json
import multiprocessing
import os
import re
import shutil
import sys
import timeit
from pprint import pprint

try:
  import jinja2
  import pygments
  import pygments.formatters as formatters
  import pygments.lexers as lexers
  import pygments.lexers.special as sp_lexer
except:
  packages = ' '.join(["jinja2", "pygments"])
  print(f"Missing required packages, one of: {packages}")
  print(f"pip3 install {packages}")
  print()
  print()

semaphore = a.BoundedSemaphore(multiprocessing.cpu_count())


#################### ###################### ####################
#################### Domain Agnostic Region ####################
#################### ###################### ####################


class colours:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'


def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)


def err_exit(*msg, code=255):
  for m in msg:
    eprint(m)
  exit(code)


def load_module(path):
  try:
    if not os.path.isfile(path):
      raise Exception(f"{path} is not a file")
    file_name, _ = os.path.splitext(os.path.basename(path))
    spec = importlib.util.spec_from_file_location(
        file_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
  except Exception as e:
    pprn(f"Error :: Failed to load filters from {path}",
         colour=colours.FAIL)
    err_exit(e)


def identity(x):
  return x


def constantly(x):
  return lambda _: x


def fst(x):
  return next(iter(x), None)


def groupby(key, items):
  s_items = sorted(items, key=key)
  g_items = i.groupby(s_items, key=fst)
  grouping = [(name, [group for _, group in groups])
              for name, groups in g_items]
  return grouping


def console_size():
  try:
    with os.popen("stty size", "r") as fd:
      rows, cols = [int(chars) for chars in fd.read().split()]
      return rows, cols
  except:
    return -1, -1


def pprn(msg, err=False, before="", after="", centre=False, colour=None):
  _, cols = console_size()
  ml = len(msg)
  cols = 20 if cols == -1 else cols
  padding = 0 if not centre or ml > cols else int((cols - ml) / 2)
  msg = f"{before * cols}\n{' ' * padding}{msg}\n{after * cols}"
  pp = eprint if err else print
  if colour:
    pp(f"{colour}{msg}{colours.ENDC}")
  else:
    pp(msg)


def find_diff(old, new):
  compare = difflib.Differ().compare
  diffs = "\n".join(compare(old.splitlines(), new.splitlines()))
  return diffs


def fd_files(chk=constantly(True), src="."):
  return [os.path.join(root, file)
          for root, _, files in os.walk(src)
          for file in files
          if chk(file)]


def fd_dirs(chk=constantly(True), src="."):
  return [os.path.join(root, dir_name)
          for root, dirs, _ in os.walk(src)
          for dir_name in dirs
          if chk(dir_name)]


def ancestry(current, celi=os.getcwd(), acc=[]):
  full = os.path.realpath(current)
  assert celi in full
  if full == celi:
    return acc
  else:
    nxt = [os.path.relpath(full)] + acc
    return ancestry(os.path.dirname(full), celi, nxt)


def mkdir(dirname):
  try:
    os.makedirs(dirname)
  except OSError as exc:
    if not os.path.isdir(dirname) or exc.errno != errno.EEXIST:
      raise


def rm_r(path):
  if os.path.isdir(path) and not os.path.islink(path):
    shutil.rmtree(path)
  elif os.path.exists(path):
    os.remove(path)


def slurp(file):
  try:
    with open(file, "r") as fd:
      return fd.read()
  except:
    return ""


def spit(content, file):
  with open(file, "w") as fd:
    fd.write(content)


async def pipe(program, *args, stdin=None):
  process = await a.create_subprocess_exec(
      *[program, *args],
      stdin=a.subprocess.PIPE,
      stdout=a.subprocess.PIPE,
      stderr=a.subprocess.PIPE)

  msg = stdin.encode() if stdin else None
  stdout, stderr = await process.communicate(msg)
  return stdout.decode(), stderr.decode(), process.returncode


#################### ####################### ####################
#################### Domain Region - Prepare ####################
#################### ####################### ####################


def load_filters(imports):
  modules = [load_module(path) for path in imports]
  injections = {name: func
                for mod in modules
                for name, func in
                inspect.getmembers(mod, inspect.isfunction)}
  return injections


def load_extra_vars(extra):
  try:
    return f.reduce(
        lambda acc, curr: {**acc, **curr},
        [json.loads(json_data)
            for json_data in extra],
        {})
  except json.decoder.JSONDecodeError as e:
    pprn(f"Error loading extra vars :: Malformed JSON",
         err=True,
         colour=colours.FAIL)
    err_exit(e, e.doc)
  except Exception as e:
    pprn(f"Error loading extra vars",
         err=True,
         colour=colours.FAIL)
    err_exit(e)


def find_j2_files(excludes, src):
  def match(fn):
    wanted = all(not exclude in fn for exclude in excludes)
    return fn.endswith(".j2") and wanted
  files = [os.path.relpath(f, src)
           for f in fd_files(src=src)
           if match(f)]
  return files


def find_var_files(names, curr, src):
  vf = [f for f in os.listdir(curr)
        if os.path.isfile(f) and f in names]
  children = [d for d in
              [os.path.join(curr, d)
               for d in os.listdir(curr)]
              if os.path.isdir(d)]
  var_files = [os.path.join(curr, f)
               for f in sorted(vf, key=lambda f: names.index(f))]
  nxt = [find_var_files(names, child, src)
         for child in children]
  path = os.path.relpath(curr, src)
  return (path, var_files, nxt)


def prepare_j2(filters, src):
  j2 = jinja2.Environment(
      enable_async=True,
      trim_blocks=True,
      lstrip_blocks=True,
      undefined=jinja2.StrictUndefined,
      loader=jinja2.FileSystemLoader(src))
  j2.filters = {**j2.filters, **filters}
  return j2


#################### ######################### ###################
#################### Domain Region - LoadVars ####################
#################### ######################## ####################


def preprocess(delimiter, stdout):
  limit = stdout.rfind(delimiter)
  if limit == -1:
    return stdout, ""
  else:
    return stdout[limit+1:], stdout[:limit]


def warn_suspicious(var_file, err, code):
  if err:
    pprn(f"Warning - {var_file} :: Unexpected stderr",
         err=True,
         colour=colours.FAIL)
    eprint(err)
  if code != 0:
    pprn(f"Warning - {var_file} :: None zero exit code - {code}",
         err=True,
         colour=colours.FAIL)


def print_comments(var_file, comments):
  if comments:
    pprn(f"Comments :: {var_file}",
         before="#")
    print(comments)


async def pipe_var(delimiter, var_file, extra_vars):
  try:
    if not os.access(var_file, os.X_OK):
      raise Exception("Insufficient privilege (chmod +x)")

    out, err, code = await pipe(var_file, stdin=json.dumps(extra_vars))
    data, comments = preprocess(delimiter, out)
    print_comments(var_file, comments)
    warn_suspicious(var_file, err, code)
    return {**extra_vars, **json.loads(data)}

  except json.decoder.JSONDecodeError as e:
    pprn(f"Error loading - {var_file} :: Malformed JSON",
         err=True,
         colour=colours.FAIL)
    err_exit(e, var_file, e.doc)
  except Exception as e:
    pprn(f"Error loading - {var_file}",
         err=True,
         colour=colours.FAIL)
    err_exit(e, var_file)


async def load_vars(inject, delimiter, var_files, curr_vars):
  dir_name, cur, nxt = var_files
  nxt_vars = {**curr_vars}
  for vf in cur:
    injected = await inject(nxt_vars, vf)
    nxt_vars = await pipe_var(delimiter, vf, injected)
  tasks = [load_vars(inject, delimiter, n, nxt_vars) for n in nxt]
  res = await a.gather(*tasks)
  v = {k: v for r in res for k, v in r.items()}
  return {dir_name: nxt_vars, **v}


#################### ########################## ####################
#################### Domain Region - Injections ####################
#################### ########################## ####################


def load_injection(injections, delimiter):
  async def inject(variables):
    nxt_vars = {**variables}
    for injection in injections:
      nxt_vars = await pipe_var(delimiter, injection, nxt_vars)
    return nxt_vars
  return inject


def inject_var_file_cxt(src, dest, injection):
  async def inject(v, var_file):
    _var_file_ = os.path.relpath(var_file, src)
    _dir_ = os.path.dirname(_var_file_)
    _parent_ = os.path.dirname(_dir_)
    _grand_parent_ = os.path.dirname(_parent_)
    context = {"_src_": src,
               "_dest_": dest,
               "_var_file_": _var_file_,
               "_dir_": _dir_,
               "_parent_": _parent_,
               "_grand_parent_": _grand_parent_}
    return await injection({**v, **context})
  return inject


def inject_render_cxt(src, dest, injection):
  async def inject(v, j2_file):
    _template_ = j2_file
    _dir_ = os.path.dirname(_template_)
    _parent_ = os.path.dirname(_dir_)
    _grand_parent_ = os.path.dirname(_parent_)
    context = {"_src_": src,
               "_dest_": dest,
               "_template_": _template_,
               "_dir_": _dir_,
               "_parent_": _parent_,
               "_grand_parent_": _grand_parent_}
    return await injection({**v, **context})
  return inject


#################### ###################### ####################
#################### Domain Region - Render ####################
#################### ###################### ####################


async def render_file(j2, j2_file, variables):
  try:
    res = await j2.get_template(j2_file).render_async(**variables)
    return res
  except Exception as e:
    path = os.path.join(*j2.loader.searchpath, j2_file)
    pprn(f"Error rendering - {path}",
         err=True,
         colour=colours.FAIL)
    if isinstance(e, jinja2.UndefinedError):
      matches = re.match(r"^'[^']+'", e.message)
      var_name = matches.group().strip("'") if matches else e
      err_exit(f"Undefined variable - {{{{ { var_name } }}}}", e)
    elif isinstance(e, jinja2.TemplateSyntaxError):
      err_exit(e, f"Line {e.lineno}: {e.name or e.filename}")
    elif isinstance(e, jinja2.TemplateNotFound):
      err_exit(f"Template not found: {e.name}")
    else:
      err_exit(e)


async def render(inject, j2, j2_files, variables):
  async def load(j2_file):
    v = variables.get(os.path.dirname(j2_file))
    injected = await inject(v, j2_file)
    return await render_file(j2, j2_file, injected)

  tasks = [load(j2_file)
           for j2_file in j2_files]
  res = await a.gather(*tasks)
  return list(zip(j2_files, res))


#################### ########################## ####################
#################### Domain Region - PostRender ####################
#################### ########################## ####################


def remove_j2_postfix(file_name):
  return re.sub(r"\.j2$", "", file_name)


def diff_changes(rendered, out):
  unchanged, updated = [], []
  dest_files = set([*fd_files(src=out)])

  for path, content in rendered:
    content_dest = remove_j2_postfix(os.path.join(out, path))
    dest_content = slurp(content_dest)

    if content_dest in dest_files:
      dest_files.discard(content_dest)

    if dest_content == content:
      unchanged += [content_dest]
    else:
      updated += [(content_dest, content, dest_content)]

  removed = [*dest_files]
  res = (sorted(unchanged),
         sorted(updated, key=fst),
         sorted(removed))
  return res


def commit_changes(out, updated, removed):
  for path, content, _ in updated:
    mkdir(os.path.dirname(path))
    spit(content, path)

  for p in removed:
    rm_r(p)

  empty_folders = [d for d in
                   fd_dirs(src=out)
                   if len(fd_files(src=d)) == 0]

  for d in empty_folders:
    rm_r(d)


#################### ######################## ####################
#################### Domain Region - Announce ####################
#################### ######################## ####################


def get_lexer(file_name):
  try:
    return lexers.get_lexer_for_filename(file_name)
  except:
    return sp_lexer.TextLexer()


def colourize(formatter, content, file_name):
  return pygments.highlight(
      content,
      lexer=get_lexer(file_name),
      formatter=formatters.get_formatter_by_name(formatter))


def announce_diffs(formatter, updated):
  for path, new, old in updated:
    diff = find_diff(old, new)
    pretty_diff = colourize(formatter, diff, path)
    pprn(f"DIFF :: {path}")
    print(pretty_diff)


def announce_changes(src, out, updated, removed):
  updated_paths = [path for path, _, _ in updated]

  def announce(type, changes):
    if len(changes):
      pprn(type, centre=True)
      for p in changes:
        path = os.path.join(src, os.path.relpath(p, out))
        print(f"{path}.j2")

  zipped = zip(
      ["REMOVED", "UPDATED"],
      [removed, updated_paths])

  for announcement in zipped:
    announce(*announcement)


#################### ############### ####################
#################### ArgParse Region ####################
#################### ############### ####################

src_help = """
Put all your .j2 templates here, along with var_files.
"""

out_help = """
Your finished templates go here.
"""

exclude_files_help = """
Any file paths in exclude will be skipped.
i.e. --exclude .s .skip
"""

var_files_help = """
A VAR_FILE is an executable: .py, .sh, et al.
VAR_FILES are how you do variable injections.
JSON - stdin |> stdout - JSON.
VAR_FILES are placed in the file hierarchy
beween *.j2 and SRC.
VAR_FILES closes to *.j2 have higher precedence.
"""

extra_vars_help = """
Inject variables with JSON.
Highest precedence, also available to all var files.
"""

inject_before_vars_help = """
Same semantics as VAR_FILES,
except run before each VAR_FILE.
"""

inject_before_render_help = """
Same semantics as VAR_FILES,
except run before each .j2 file is rendered.
"""

imports_filters_help = """
All functions in IMPORT_FILTERS will be included as
j2 filters. Must be python files.
"""


delimiter_help = """
Default is 🦄.
Any stdout in VAR_FILES before the last occurance
of 🦄 will be treated as comments.
🦄 is entirely optional.
"""

dry_run_help = """
Just do a diff, dont write to file.
"""

no_diffs_help = """
Dont print diff.
"""

formatter_help = """
Used to print diff, if your terminal is kinda wonky,
pick one with less colours.
"""


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "-s", "--src",
      required=True,
      help=src_help)
  parser.add_argument(
      "-o", "--out",
      required=True,
      help=out_help)
  parser.add_argument(
      "-v", "--var-files",
      required=True,
      nargs="+",
      default=[],
      help=var_files_help)
  parser.add_argument(
      "-k", "--exclude",
      nargs="+",
      default=[],
      help=exclude_files_help
  )
  parser.add_argument(
      "-f", "--import-filters",
      nargs="*",
      default=[],
      help=imports_filters_help)
  parser.add_argument(
      "--inject-before-vars",
      nargs="+",
      default=[],
      help=inject_before_vars_help)
  parser.add_argument(
      "--inject-before-render",
      nargs="+",
      default=[],
      help=inject_before_render_help)
  parser.add_argument(
      "-e", "--extra-vars",
      nargs="*",
      default=[],
      help=extra_vars_help)
  parser.add_argument(
      "--delimiter",
      default="🦄",
      help=delimiter_help)
  parser.add_argument(
      "-d", "--dry-run",
      action="store_true",
      help=dry_run_help)
  parser.add_argument(
      "-n", "--no-diffs",
      action="store_true",
      help=no_diffs_help)
  parser.add_argument(
      "--formatter",
      choices=["terminal16m", "terminal256", "terminal", "null"],
      default="terminal16m",
      help=formatter_help)
  return parser.parse_args()


#################### #################### ####################
#################### Domain Region - Main ####################
#################### #################### ####################


async def main():
  t1 = timeit.default_timer()
  args = parse_args()

  inj_v = load_injection(args.inject_before_vars, args.delimiter)
  inj_r = load_injection(args.inject_before_render, args.delimiter)

  inject_v = inject_var_file_cxt(args.src, args.out, inj_v)
  inject_r = inject_render_cxt(args.src, args.out, inj_r)

  filters = load_filters(args.import_filters)
  extra_vars = load_extra_vars(args.extra_vars)
  j2_files = find_j2_files(args.exclude, args.src)
  var_files = find_var_files(args.var_files, args.src, args.src)
  j2 = prepare_j2(filters, args.src)

  variables = await load_vars(
      inject_v,
      args.delimiter,
      var_files,
      extra_vars)

  rendered = await render(
      inject_r,
      j2,
      j2_files,
      variables)

  unchanged, updated, removed = diff_changes(rendered, args.out)

  if args.dry_run:
    pprn("DRY RUN", before="$", centre=True)
  else:
    commit_changes(args.out, updated, removed)

  if not args.no_diffs:
    announce_diffs(args.formatter, updated)

  announce_changes(
      args.src,
      args.out,
      updated,
      removed)

  total = len(updated) + len(unchanged)
  t2 = timeit.default_timer()
  delta = str(datetime.timedelta(seconds=t2-t1))
  pprn(f"Rendered {total} files in {delta}s", centre=True)


if __name__ == "__main__":
  loop = a.get_event_loop()
  loop.run_until_complete(main())
  loop.close()
