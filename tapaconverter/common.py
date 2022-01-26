import logging
import re

from typing import *

# note that the suffix must be .cpp otherwise ctags will not work
TEMP_FILE_PATH = '/tmp/tapaconverter.cpp'

def get_func_range(raw_code: str, top_name: str) -> Tuple[int, int]:
  
  match_type = '[a-zA-Z0-9_<>:]+'
  match_mandatory_space = '[ ]+'
  match_optional_space = '[ ]*'
  
  match = re.search(rf'{match_type}{match_mandatory_space}{top_name}{match_optional_space}\(', raw_code)
  if not match:
    logging.error(f'fail to locate the top function')
    raise NotImplementedError
  start_index = match.start()

  raw_code_crop = raw_code[start_index:]
  stack = 0
  init_flag = False
  for i, char in enumerate(raw_code_crop):
    if char == '{':
      init_flag = True
      stack += 1
    elif char == '}':
      stack -= 1
    if init_flag and stack == 0:
      return (start_index, start_index + i)

  assert False, f'Missing "}}" in the top function'