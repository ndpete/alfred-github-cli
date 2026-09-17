#!/bin/bash
set -e

_thisdir=$(realpath "$(dirname "$0")")
_repodir=$(realpath "${_thisdir}/../")
_dirname=$(basename "${_repodir}")

# Find Alfred preferences directory
_prefs_dir=""

# Check modern Alfred prefs.json (Alfred 4/5)
if [ -f "$HOME/Library/Application Support/Alfred/prefs.json" ]; then
    _prefs_dir=$(plutil -extract current raw "$HOME/Library/Application Support/Alfred/prefs.json" 2>/dev/null || true)
fi

# Fallback paths if prefs.json didn't yield a valid directory
if [ -z "$_prefs_dir" ] || [ ! -d "$_prefs_dir" ]; then
    for candidate in \
        "$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences" \
        "$HOME/Library/Application Support/Alfred 5/Alfred.alfredpreferences" \
        "$HOME/Library/Application Support/Alfred 4/Alfred.alfredpreferences" \
        "$HOME/Library/Application Support/Alfred 3/Alfred.alfredpreferences"; do
        if [ -d "$candidate" ]; then
            _prefs_dir="$candidate"
            break
        fi
    done
fi

if [ -z "$_prefs_dir" ] || [ ! -d "$_prefs_dir" ]; then
    echo "ERROR: Could not find Alfred preferences directory" >&2
    exit 1
fi

_workflows_dir="${_prefs_dir}/workflows"
mkdir -p "$_workflows_dir"
_target="${_workflows_dir}/${_dirname}"

echo "Linking \"${_dirname}\" to Alfred workflows at: ${_target}"

# Check if target is an existing non-symlink file or directory
if ([ -f "$_target" ] || [ -d "$_target" ]) && [ ! -L "$_target" ]; then
    echo "ERROR: Target exists and is an actual file or directory: ${_target}" >&2
    echo "Please remove or back up the existing directory before linking." >&2
    exit 1
fi

ln -hfs "$_repodir" "$_target"
echo "Successfully linked ${_dirname} to Alfred workflows!"
