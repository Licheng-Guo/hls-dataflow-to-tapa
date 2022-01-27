import logging
import re

from typing import *
from tapaconverter.AnalyzeStreamDirectionByOperation import Param, Func, extract_functions

class FuncCall:
  def __init__(
      self, 
      name: str, 
      caller: Func, 
      callee: Func, 
      caller_arg_list: List[str],
  ):
    self.name = name
    self.caller = caller
    self.callee = callee
    self.caller_arg_list = caller_arg_list
    self.callee_param_list = callee.get_param_list()


class HierFunc(Func):
  def __init__(self, name, func_type, func_range: Tuple[int, int], text, name_to_func: Dict[str, Func]):
    self.name = name
    self.func_type = func_type
    self.func_range = func_range
    self.text = text
    self.name_to_func = name_to_func
    self.name_to_param: Dict[str, Param] = {param.param_name: param for param in self.get_param_list()}
    self.param_list_range: Tuple[int, int] = self.update_param_list_range()


def get_func_calls(curr_func: Func, name_to_func: Dict[str, Func]) -> List[FuncCall]:
  """
  extract all func calls within the given function
  """
  func_call_list = []
  for candidate_func_name, candidate_func in name_to_func.items():
    # filter out self
    if candidate_func_name == curr_func.name:
      continue

    # use ';' to differentiate a func call from the caller signature
    match = re.search(rf'({candidate_func_name})\s*\(([^)]*)\s*\);', curr_func.text)  # no need to findall
    if match:
      func_call_name = match.group(1)
      func_call_arg_str = match.group(2)
      func_call_arg_list = [arg.strip() for arg in func_call_arg_str.split(',')]

      func_call_list.append(FuncCall(func_call_name, curr_func, candidate_func, func_call_arg_list))

  return func_call_list


def get_func_to_func_calls(func_list: List[Func]) -> Dict[Func, List[FuncCall]]:
  """
  get the mapping from all functions to the function calls within
  """
  name_to_func = {func.name : func for func in func_list}
  func_to_func_calls = {func: get_func_calls(func, name_to_func) for func in func_list}
  return func_to_func_calls


def populate_stream_dir(func_list: List[Func]) -> None:
  """
  derive stream directions based on function calls
  """
  func_to_func_calls = get_func_to_func_calls(func_list)

  for func, func_call_list in func_to_func_calls.items():
    for func_call in func_call_list:
      for i, param in enumerate(func_call.callee_param_list):
        if 'stream' in param.param_type:
          found_stream_var = func_call.caller_arg_list[i]
          stream_var_direction = param.param_type
          func.check_and_update_param_type_by_name(found_stream_var, stream_var_direction)



# given the filename, first extract all functions
# for each function, extract the parameters and the stream operations
# match stream operations with parameters
# next, extract all funccalls, match the parameter of callees with the variables
# then update the params of callers
# repeat this process until nothing changed