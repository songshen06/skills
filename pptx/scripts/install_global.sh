#!/usr/bin/env bash
set -e
SRC="/Users/shens/Downloads/skills-main/.trae/skills/pptx/"
DST="$HOME/.trae/skills/pptx"
mkdir -p "$DST"
rsync -a --delete "$SRC" "$DST/"
