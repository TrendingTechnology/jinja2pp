#!/usr/bin/env python3

import json
import sys
from pprint import pprint

variables_in = json.load(sys.stdin)


# Merge in new Variables
# Overwrite previous Variables
# Whatever you want!

extra = dict(

)

variables_out = {**variables_in, **extra}
print("🦄")  # Parsing Directive
json.dump(variables_out, sys.stdout)
