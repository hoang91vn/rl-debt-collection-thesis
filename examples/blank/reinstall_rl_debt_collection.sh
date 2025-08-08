#!/bin/sh
rm -rf uv.lock
uv sync --offline --reinstall-package rl-debt-collection
