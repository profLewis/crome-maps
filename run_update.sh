#!/bin/bash
# Wrapper for launchd — sets up environment and runs update_datasets.py
# launchd strips all environment, so we must set everything explicitly.
export HOME="/Users/plewis"
export PATH="/Users/plewis/anaconda3/bin:/usr/local/bin:/usr/bin:/bin"
export PYTHONHOME="/Users/plewis/anaconda3"
cd /Users/plewis/Documents/GitHub/crome-maps || exit 1
exec /Users/plewis/anaconda3/bin/python3 -u update_datasets.py --discover "$@"
