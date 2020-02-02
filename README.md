# [Jinja2++](https://ms-jpq.github.io/jinja2pp/)

Jinja2++ is a drop in single file solution for templating with **Variable Precedence**.

You can use **ANY language!**

## Features

### Variable precedence

```txt
src
|── vars.py* <- [[base variables]]
├── filters.py* <- inject ((J2 filters)) with ~vanilla python~ functions!
├── render_inject.py* <- inject && overwrite [pre-render context] variables
├── var_inject.py* <- inject && overwrite [pre-script context] variables 
...
├── monitoring/
│  ├── grafana/
│  │  ├── templates/
│  │  ├── Chart.yaml.j2
│  │  └── vars.sh* <- [overwrite] variables here
│  ├── iperf/
│  │  ├── templates/
│  │  ├── Chart.yaml.j2
│  │  └── vars.py* <- [overwrite] variables here
│  ├── prometheus/
│  │  ├── templates/
│  │  ├── Chart.yaml.j2
│  │  └── vars.rb* <- [overwrite] variables here
...
```

### Dry runs

![dryrun](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/dryrun.png)

![res](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/res.png)

### Syntax highlighted diff

![diff1](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/diff1.png)

![diff2](https://raw.githubusercontent.com/ms-jpq/jinja2pp/master/screenshot/diff2.png)

### Context injection

### Dynamic J2 filter import
