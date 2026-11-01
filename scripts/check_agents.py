#!/usr/bin/env python3
"""Reject edits outside project settings and incomplete setup in an adopted AGENTS.md."""
import argparse
from pathlib import Path
import re
import sys

BEGIN = '<!-- BEGIN PROJECT SETTINGS -->'
END = '<!-- END PROJECT SETTINGS -->'


def split_document(text):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Expected exactly one pair of project settings markers.')
    before, rest = text.split(BEGIN)
    if END not in rest:
        raise ValueError('Project settings markers are out of order.')
    settings, after = rest.split(END)
    return before, settings, after


def validate(template, installed, allow_unconfigured=False):
    before, template_settings, after = split_document(template)
    actual_before, settings, actual_after = split_document(installed)
    if (before, after) != (actual_before, actual_after):
        raise ValueError('Shared workflow differs from the pinned template. Explicit workflow-update approval is required.')
    field = r'^(- [^:\n]+: ).*$'
    skeleton = lambda text: re.sub(field, r'\1<VALUE>', text, flags=re.MULTILINE)
    if skeleton(template_settings) != skeleton(settings):
        raise ValueError('Change only existing setting values; preserve field names and surrounding text.')
    if not allow_unconfigured:
        values = re.findall(r'^- [^:\n]+: (.*)$', settings, flags=re.MULTILINE)
        if any(not value.strip().strip('`').strip() for value in values):
            raise ValueError('Empty project settings remain.')
        flags = re.findall(r'^- Setup confirmed: (.*)$', settings, flags=re.MULTILINE)
        if flags != ['yes']:
            raise ValueError('Setup must be explicitly confirmed by the user before work starts.')
        if re.search(r'<[^>\n]+>', settings):
            raise ValueError('Unfilled project settings remain.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, required=True, help='Pinned, unmodified upstream AGENTS.md template')
    parser.add_argument('--agents', type=Path, default=Path('AGENTS.md'))
    parser.add_argument('--allow-unconfigured', action='store_true', help='Setup-only: check shared text without requiring filled settings')
    args = parser.parse_args()
    try:
        validate(args.template.read_text(), args.agents.read_text(), args.allow_unconfigured)
    except (OSError, ValueError) as error:
        print(f'AGENTS.md validation failed: {error}', file=sys.stderr)
        return 1
    print('AGENTS.md matches its pinned shared workflow' + (' (setup-only check).' if args.allow_unconfigured else '; settings are filled and marked confirmed.'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
