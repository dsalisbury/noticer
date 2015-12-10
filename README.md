# `noticer` -- for rerunning commands

## What is `noticer`?

I wanted a way to rerun a command when files changed, killing the old process
beforehand if required; `noticer` achieves this. Under the hood it uses inotify
(via [pyinotify](https://pypi.python.org/pypi/pyinotify)), handling CREATE and
MODIFY events.


## How do I install `noticer`?

You can install straight from Github: 

``
$ pip install https://github.com/dsalisbury/noticer/archive/master.zip
``
