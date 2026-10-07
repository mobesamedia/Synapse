"""Bounded SVG geometry embedded in FreeMap documents; never executable markup."""
import math
import re

ATTRS = {
    'path': {'d'}, 'line': {'x1', 'y1', 'x2', 'y2'},
    'polyline': {'points'}, 'polygon': {'points'},
    'circle': {'cx', 'cy', 'r'}, 'ellipse': {'cx', 'cy', 'rx', 'ry'},
    'rect': {'x', 'y', 'width', 'height', 'rx', 'ry'},
}
KEY = re.compile(r'^[a-zA-Z0-9_-]{1,120}$')
PATH = re.compile(r'^[MmLlHhVvCcSsQqTtAaZz0-9eE.,+\s-]{1,16000}$')
POINTS = re.compile(r'^[0-9eE.,+\s-]{1,16000}$')


def valid_definition(value):
    if not isinstance(value, dict) or set(value) != {'name', 'nodes'}:
        return False
    if not isinstance(value['name'], str) or not 1 <= len(value['name']) <= 100:
        return False
    nodes = value['nodes']
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 64:
        return False
    length = 0
    for node in nodes:
        if not isinstance(node, list) or len(node) != 2:
            return False
        tag, attrs = node
        if not isinstance(tag, str) or tag not in ATTRS or not isinstance(attrs, dict) or not attrs or not set(attrs) <= (ATTRS[tag] | {'fill'}):
            return False
        for key, val in attrs.items():
            if not isinstance(val, str) or len(val) > 16000:
                return False
            length += len(val)
            if key == 'fill':
                if val not in ('none', 'currentColor'):
                    return False
            elif key in ('d', 'points'):
                if not (PATH if key == 'd' else POINTS).fullmatch(val):
                    return False
            else:
                try:
                    number = float(val)
                    if not math.isfinite(number) or abs(number) > 10000:
                        return False
                except ValueError:
                    return False
    return length <= 32000


def validate_document(document):
    definitions = document.get('iconAssets', {})
    if not isinstance(definitions, dict) or len(definitions) > 512:
        raise ValueError('Invalid icon assets')
    for key, value in definitions.items():
        if not isinstance(key, str) or not KEY.fullmatch(key) or not valid_definition(value):
            raise ValueError('Invalid icon geometry')
    for obj in document.get('objects', []):
        if isinstance(obj, dict) and obj.get('kind') == 'icon':
            if not isinstance(obj.get('icon'), str) or obj['icon'] not in definitions:
                raise ValueError('Missing icon geometry')
    license_text = document.get('iconLicense', '')
    if not isinstance(license_text, str) or len(license_text) > 16000:
        raise ValueError('Invalid icon license')
