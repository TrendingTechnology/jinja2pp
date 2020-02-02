# [Jinja2++](https://ms-jpq.github.io/jinja2pp/)

Jinja2++ is a drop in single file solution for templating with **Variable Precedence**.

You can use **ANY language!**

## Features

### Variable precedence

```txt
src
|── vars.perl* <- [[base variables]]
├── filters.py* <- inject ((J2 filters)) with ~vanilla python~ functions!
...
├── render_inject.rb* <- inject && overwrite [pre-render context] variables
├── var_inject.sh* <- inject && overwrite [pre-script context] variables 
...
├── monitoring/
│  ├── grafana/
│  │  ├── templates/
│  │  ├── Chart.yaml.j2
│  │  └── vars.js* <- [overwrite] variables here
│  ├── iperf/
│  │  ├── templates/
│  │  ├── Chart.yaml.j2
│  │  └── vars.fsi* <- [overwrite] variables here
│  ├── prometheus/
│  │  ├── templates/
│  │  ├── Chart.yaml.j2
│  │  └── vars.exe* <- [overwrite] variables here
...
```

### Dry runs

![dryrun](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/dryrun.png)

![res](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/res.png)

### Syntax highlighted diff

![diff1](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/diff1.png)

![diff2](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/diff2.png)

### Dynamic J2 filter import

Write your filters as vanilla Python functions.

like so:

```python
def drop_first(lst):
  return lst[1:]


def base64(x, indent=0):
  encoded = str(b64.b64encode(x.strip().encode("utf-8")), "utf-8")
  return (" " * indent) + (encoded if encoded else "")
```

### Context injection

The following `[context variables]` will be injected before each var_file / template.

add more of your own!

```json
{"src": "...",
 "_dest_": "...",
 "_dir_": "...",
 "_parent_": "...",
 "_grand_parent_": "...",
 "_var_file_/_template_": "..."}
```

## Usage

`--src`

Put all your .j2 templates here.

`--out`

Your finished templates go here.

`--exclude`

Any file paths in exclude will be skipped. i.e. --exclude .s .skip


`--var-files`

A |VAR_FILE| is an executable: .py, .sh, et al.
|VAR_FILES| are how you do variable injections.
JSON |> stdin >=> stdout |> JSON.
|VAR_FILES| are placed in the file hierarchy
beween *.j2 and SRC.
|VAR_FILES| closes to *.j2 have higher precedence.


`--import-filters`

All functions in IMPORT_FILTERS will be included as
j2 filters. Must be python files.


`--inject-before-vars`

Same semantics as |VAR_FILES|,
except run before each |VAR_FILE|.


`--inject-before-render`

Same semantics as |VAR_FILES|,
except run before each .j2 file is rendered.


`--extra-vars`

Inject variables with JSON.
Highest precedence, also available to all var files.


`--delimiter`

Default is 🦄.
Any stdout in VAR_FILES before the last occurance
of 🦄 will be treated as comments.
🦄 is entirely optional.


`--dry-run`

Just do a diff, dont write to file.


`--no-diffs`

Dont print diff.


`--formatter`

Used to print diff, if your terminal is kinda wonky,
pick one with less colours.

