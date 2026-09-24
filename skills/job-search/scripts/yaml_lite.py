"""Minimal YAML subset for job-search config files. Standard library only.

Supported: nested mappings with space indentation, block lists of scalars or
of flat mappings, flow lists of scalars ([a, "b"]), scalars (str, int, float,
true/false, null), and # comments. Anything else raises ValueError.
"""
import json
import re

_KEY = re.compile(r'^([A-Za-z0-9_\-]+):(?:\s+(.*))?$')
_PLAIN = re.compile(r'^[A-Za-z0-9_./@+\-][A-Za-z0-9_./@+\- ]*$')
_NUMBER = re.compile(r'^-?\d+(\.\d+)?$')


def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote and line[i - 1] != '\\':
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            break
        out.append(ch)
    return ''.join(out).rstrip()


def _lines(text):
    result = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        result.append([indent, line.strip()])
    return result


def _split_flow(inner):
    items, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            buf.append(ch)
        elif ch == ',':
            items.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = ''.join(buf).strip()
    if tail:
        items.append(tail)
    return items


def scalar(s):
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        return [scalar(x) for x in _split_flow(s[1:-1])]
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return json.loads(s)
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    low = s.lower()
    if low == 'true':
        return True
    if low == 'false':
        return False
    if low in ('null', '~'):
        return None
    if re.fullmatch(r'-?\d+', s):
        return int(s)
    if re.fullmatch(r'-?\d+\.\d+', s):
        return float(s)
    return s


def _is_item(content):
    return content == '-' or content.startswith('- ')


def _parse_block(lines, i, indent):
    if _is_item(lines[i][1]):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines, i, indent):
    obj = {}
    while i < len(lines) and lines[i][0] == indent and not _is_item(lines[i][1]):
        m = _KEY.match(lines[i][1])
        if not m:
            raise ValueError('expected "key: value", got: %r' % lines[i][1])
        key, rest = m.group(1), m.group(2)
        i += 1
        if rest:
            obj[key] = scalar(rest)
        elif i < len(lines) and lines[i][0] > indent:
            obj[key], i = _parse_block(lines, i, lines[i][0])
        elif i < len(lines) and lines[i][0] == indent and _is_item(lines[i][1]):
            obj[key], i = _parse_list(lines, i, indent)
        else:
            obj[key] = None
    if i < len(lines) and lines[i][0] > indent:
        raise ValueError('unexpected indent at: %r' % lines[i][1])
    return obj, i


def _parse_list(lines, i, indent):
    items = []
    while i < len(lines) and lines[i][0] == indent and _is_item(lines[i][1]):
        rest = lines[i][1][1:].strip()
        if not rest:
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                item, i = _parse_block(lines, i, lines[i][0])
            else:
                item = None
        elif _KEY.match(rest):
            lines[i] = [indent + 2, rest]
            item, i = _parse_map(lines, i, indent + 2)
        else:
            item = scalar(rest)
            i += 1
        items.append(item)
    return items, i


def load(text):
    lines = _lines(text)
    if not lines:
        return {}
    obj, i = _parse_block(lines, 0, lines[0][0])
    if i != len(lines):
        raise ValueError('could not parse line: %r' % lines[i][1])
    return obj


def _fmt(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    if (_PLAIN.match(s) and s == s.strip() and not _NUMBER.match(s)
            and s.lower() not in ('true', 'false', 'null', '~')):
        return s
    return json.dumps(s, ensure_ascii=False)


def _flow(values):
    return '[%s]' % ', '.join(_fmt(x) for x in values)


def dump(obj, indent=0):
    pad = ' ' * indent
    out = []
    for key, val in obj.items():
        if isinstance(val, dict):
            out.append('%s%s:' % (pad, key))
            if val:
                out.append(dump(val, indent + 2))
        elif isinstance(val, list) and all(not isinstance(x, (dict, list)) for x in val):
            out.append('%s%s: %s' % (pad, key, _flow(val)))
        elif isinstance(val, list):
            out.append('%s%s:' % (pad, key))
            for item in val:
                if not isinstance(item, dict) or not item:
                    raise ValueError('block lists must hold non-empty flat mappings')
                for n, (k2, v2) in enumerate(item.items()):
                    prefix = pad + ('  - ' if n == 0 else '    ')
                    if isinstance(v2, dict):
                        raise ValueError('nested mapping inside a list item is not supported')
                    shown = _flow(v2) if isinstance(v2, list) else _fmt(v2)
                    out.append('%s%s: %s' % (prefix, k2, shown))
        else:
            out.append('%s%s: %s' % (pad, key, _fmt(val)))
    return '\n'.join(out)
