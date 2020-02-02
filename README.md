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


### Syntax highlighted diff

### Dry runs

### Context injection

### Dynamic J2 filter import
