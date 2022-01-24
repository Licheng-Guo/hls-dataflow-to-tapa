import logging
import re

from tapaconverter.ParseTop import get_top_func_range
from tapaconverter.TraverseTopAST import get_tapa_top


def replace_hls_stream(raw_code: str) -> str:
  _temp_code = raw_code
  _temp_code = re.sub(r'hls::stream', 'tapa::istream', _temp_code)
  _temp_code = re.sub(r'read_nb', 'try_read', _temp_code)
  _temp_code = re.sub(r'write_nb', 'try_write', _temp_code)
  return _temp_code

def replace_top_func(raw_code: str, top_name: str, tapa_top_func: str) -> str:
  start_index, end_index = get_top_func_range(raw_code, top_name)
  return raw_code[:start_index] + tapa_top_func + raw_code[end_index+1:]


def get_tapa_init_version(top_path, top_name) -> str:
  _temp_code = open(top_path, 'r').read()
  _temp_code = replace_hls_stream(_temp_code)
  _temp_code = replace_top_func(_temp_code, top_name, get_tapa_top(top_path, top_name))
  return _temp_code