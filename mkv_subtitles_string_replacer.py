import argparse
import json
import os
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description='Replaces strings in the first .ass subs of an mkv file and remuxes it')
parser.add_argument('--input', type=str, help='The input mkv file')


STREAM_MAP_RE = re.compile(r'.+Stream\s#(?P<stream_map>\d+:\d+)')
ORIGINAL_SUBS_FILENAME = 'original_subs.ass'
STRING_REPLACEMENT_MAPPING_FILENAME = 'string_mapping.json'
NEW_SUBS_FILENAME = 'new_subs.ass'
FIXED_FILE_SUFFIX = ' [String Remapped]'


def delete_file(filename):
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass


def get_sub_stream_map(filename):
    mkv_info = subprocess.run(
        ['ffprobe', filename],
        capture_output=True,
        check=True,
    )
    subtitle_streams = filter(
        lambda line: b'Stream' in line and b'Subtitle' in line,
        mkv_info.stderr.split(b'\n'),
    )
    sub_stream_map = STREAM_MAP_RE.match(str(next(subtitle_streams))).groupdict()['stream_map']
    return sub_stream_map


def extract_subs(filename, sub_stream_map):
    delete_file(ORIGINAL_SUBS_FILENAME)
    subprocess.run(
        ['ffmpeg', '-i', filename, '-map', sub_stream_map, '-c:s', 'ass', ORIGINAL_SUBS_FILENAME],
        check=True,
    )


def replace_strings_in_subs(subs_filename):
    with open(STRING_REPLACEMENT_MAPPING_FILENAME, 'r') as fh:
        string_mapping = json.loads(fh.read())
    with open(ORIGINAL_SUBS_FILENAME, 'r') as fh:
        sub_lines = fh.readlines()

    new_lines = []
    for line in sub_lines:
        for key, value in string_mapping.items():
            line = line.replace(key, value)
        new_lines.append(line)
    with open(NEW_SUBS_FILENAME, 'w') as fh:
        fh.write(''.join(new_lines))


def remux_video(filename):
    subprocess.run(
        [
            'ffmpeg', '-i', filename, '-i', NEW_SUBS_FILENAME,
            '-map', '0', '-map', '-0:s:0', '-map', '1:s', '-disposition:s:0', 'default',
            '-c', 'copy', f'{Path(filename).stem}{FIXED_FILE_SUFFIX}{Path(filename).suffix}',
        ],
        check=True,
    )


def cleanup():
    delete_file(ORIGINAL_SUBS_FILENAME)
    delete_file(NEW_SUBS_FILENAME)


def replace_mkv_subtitle_strings(filename):
    sub_stream_map = get_sub_stream_map(filename)
    extract_subs(filename, sub_stream_map)
    replace_strings_in_subs(ORIGINAL_SUBS_FILENAME)
    remux_video(filename)
    cleanup()


if __name__ == '__main__':
    args = parser.parse_args()
    replace_mkv_subtitle_strings(args.input)
