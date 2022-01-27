# first extract the raw code of each task
# search for all occurrence of .write(), .read(), .try_write(), .try_read()
# use a dict to track the variable and the direction
# most likely there will be no assignment of stream, and the var should directly correspond to the func argument
# there may be hierarchical func call
# if a stream var is passed as parameter to another function, then we need to first analyze the inner function

import logging
import re
import subprocess

from typing import *
from tapaconverter.common import get_func_range

STREAM_DIRECTION = {
  'write': 'ostream',
  'try_write': 'ostream',
  'read': 'istream',
  'try_read': 'istream',
}


class Param:
  """
  represent a stream parameter
  """
  def __init__(self, param_name, param_type, orig_text):
    self.param_name = param_name
    self.param_type = param_type
    self.orig_text = orig_text

  def update_stream_dir(self, stream_dir):
    assert 'stream' in self.param_type
    assert '::' not in stream_dir
    self.param_type = re.sub('stream', stream_dir, self.param_type)

  def __eq__(self, other):
    """
    only check about name, not type
    """
    return self.param_name == other.param_name

  def get_text(self):
    return f'{self.param_type} {self.param_name}'


class Func:
  def __init__(self, name, func_type, func_range: Tuple[int, int], text):
    self.name = name
    self.func_type = func_type
    self.func_range = func_range
    self.text = text
    self.name_to_param: Dict[str, Param] = {param.param_name: param for param in self.get_param_list()}
    self.param_list_range: Tuple[int, int] = self.update_param_list_range()

  def update_param_list_range(self) -> Tuple[int, int]:
    self.param_list_range = re.search(rf'{self.func_type}\s+{self.name}\s*\(([^)]+)\)', self.text).span(1)
    return self.param_list_range

  def get_param_list(self) -> List[Param]:
    raw_param_list = re.search(rf'{self.func_type}\s+{self.name}\s*\(([^)]+)\)', self.text).group(1).split(',')
    param_list = []
    for raw_param in raw_param_list:
      param_name = re.search(r'[ \t\n*&](\S+)\s*$', raw_param).group(1)
      param_type = re.search(r'\s*(.*[ \t\n*&])\S+\s*$', raw_param).group(1)
      param_list.append(Param(param_name, param_type, raw_param.strip()))
    return param_list

  def get_stream_var_to_dir(self) -> Dict[str, str]:
    """
    find all variables that are being read from or written to
    """
    var_op_list = re.findall(r'(\S+)\.(read|try_read|write|try_write)', self.text)
    return {var: STREAM_DIRECTION[op] for var, op in var_op_list}

  def get_stream_param_list(self) -> List[Param]:
    param_list = self.get_param_list()
    return [param for param in param_list if 'stream' in param.param_type]

  def update_param(self, updated_param: Param) -> None:
    assert 'stream' in updated_param.param_type
    self.name_to_param[updated_param.param_name] = updated_param

    # always keep the text and the param list in sync
    all_param_text = ', '.join([param.get_text() for param in self.name_to_param.values()])
    self.text = self.text[:self.param_list_range[0]] + all_param_text + self.text[self.param_list_range[1]:]
    self.update_param_list_range()

  def check_and_update_param_type_by_name(self, updated_param_name: str, updated_param_type: str) -> bool:
    """
    if already up-to-date, return False. Else return true
    """
    if updated_param_name not in self.name_to_param:
      assert False, f'trying to update a non-existing param: {updated_param_name}'
    
    if updated_param_type == self.name_to_param[updated_param_name].param_type:
      return False
    else:
      self.name_to_param[updated_param_name].param_type = updated_param_type
      self.update_param(self.name_to_param[updated_param_name])

      return True

  def get_text(self) -> str:
    """
    FIXME: make sure the text is up-to-date
    """
    # self.update_param_list_range()
    # all_param_text = ', '.join([param.get_text() for param in self.name_to_param.values()])
    # self.text = self.text[:self.param_list_range[0]] + all_param_text + self.text[self.param_list_range[1]:]
    return self.text


def update_stream_dir_by_operation(func: Func) -> None:
  """
  """
  stream_param_list = func.get_stream_param_list()
  stream_var_to_dir = func.get_stream_var_to_dir()
  if len(stream_param_list) != len(stream_var_to_dir):
    logging.debug(f'detect sub function calls with stream parameters')
  
  stream_name_to_param: Dict[str, Param] = {param.param_name: param for param in stream_param_list}
  for stream_var, stream_dir in stream_var_to_dir.items():
    if stream_var in stream_name_to_param:
      updated_stream_param = stream_name_to_param[stream_var]
      updated_stream_param.update_stream_dir(stream_dir)
      func.update_param(updated_stream_param)


def extract_functions(filename: str) -> List[Func]:
  # use ctags to extract all function names
  assert filename.endswith('.cpp'), f'the file must have extension .cpp in order for ctags to work'
  out, err = subprocess.Popen(['ctags', '-x', '--c++-kinds=fp', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  func_tags = out.decode('utf-8').strip().split('\n')

  func_list = []
  whole_file = open(filename, 'r').read()
  for tag in func_tags:
    func_name = re.search(r'(\S+)\s+function', tag).group(1)
    func_type = re.search(rf'{filename}\s+(\S+)\s+{func_name}', tag).group(1)

    func_range = get_func_range(whole_file, func_name)
    func_text = whole_file[func_range[0]: func_range[1]]
    func_list.append(Func(func_name, func_type, func_range, func_text))
  
  return func_list

