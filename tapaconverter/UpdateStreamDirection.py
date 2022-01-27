from functools import cmp_to_key
from typing import *
from tapaconverter.AnalyzeStreamDirectionByOperation import (
  extract_functions, 
  update_stream_dir_by_operation, 
  Func,
)
from tapaconverter.AnalyzeStreamDirectionByFuncCall import populate_stream_dir
from tapaconverter.common import get_func_range



def update_whole_file(whole_file: str, updated_func: Func) -> str:
  """
  first determine the range of the function in the whole file
  then replace
  """
  func_range = get_func_range(whole_file, updated_func.name)
  return whole_file[:func_range[0]] + updated_func.get_text() + whole_file[func_range[1]:]


def update_stream_directions(filename, top_name) -> str:
  func_list: List[Func] = extract_functions(filename)
  # filter out the top func
  func_list = [func for func in func_list if func.name != top_name]

  curr_text = open(filename, 'r').read()

  # update params based on stream operations
  for func in func_list:
    update_stream_dir_by_operation(func)
    curr_text = update_whole_file(curr_text, func)

  # update params based on subcalls
  for _ in range(10):  # FIXME
    populate_stream_dir(func_list)
    for func in func_list:
      curr_text = update_whole_file(curr_text, func)

  return curr_text