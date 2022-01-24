import logging
import re

from typing import *
from pycparser import c_parser, c_ast, parse_file


def get_fake_type(template_type: str) -> str:
  return template_type.replace('<', '_ANGLE_BRACKET_BEG_') \
                      .replace('>', '_ANGLE_BRACKET_END_') \
                      .replace('::', '_DOUBLE_COLON_') \
                      .replace(' ', '_SPACE_')


def get_orig_type(fake_type: str) -> str:
  return fake_type.replace('_ANGLE_BRACKET_BEG_', '<') \
                  .replace('_ANGLE_BRACKET_END_', '>') \
                  .replace('_DOUBLE_COLON_', '::') \
                  .replace('_SPACE_', ' ')


def get_all_template_types(raw_code: str) -> List[str]:
  raw_code_no_return = re.sub(r'\n', r' ', raw_code)

  # [^ \n\t(<]* match the template name before "<". Use "(" to filter out cases like for (ap_uint<32> i, ...)
  regexp_template_name = r'[^ \n\t(<]*'

  # [ ]* matches potential spaces between template name and the "<"
  regexp_space = r'[ ]*'

  # [ ]*[^<>\t\n]+[ ]* matches the parameter to instantiate the tamplate. 
  # Note that we do not consider nested templates here
  regexp_template_param = r'[^<>\t\n(){}*&;]+'

  final_regexp = rf'{regexp_template_name}{regexp_space}<{regexp_template_param}>'
  init_list = list(set(re.findall(final_regexp, raw_code_no_return)))

  filtered_list = [pattern for pattern in init_list 
                    if '#include' not in pattern 
                    and 'template' not in pattern]

  return filtered_list


def replace_template_type(raw_code: str, template_type_list: List[str]) -> str:

  _replace_template_type = lambda raw_code, template_type: \
      re.sub(template_type, get_fake_type(template_type), raw_code)

  for template_type in template_type_list:
    raw_code = _replace_template_type(raw_code, template_type)

  return raw_code


def add_fake_template_types_def(raw_code: str, template_types: List[str]) -> str:
  """
  define an empty struct for each fake type
  The fake types cannot be invoked. FIXME: tasks cannot be templates
  """
  fake_type_def_list = []
  for template_type in template_types:
    fake_type = get_fake_type(template_type)
    fake_type_def = f'typedef struct {fake_type} {{}} {fake_type};'
    fake_type_def_list.append(fake_type_def)
  # fake_type_def_list.append('// end definitions of fake types')

  next_code = fake_type_def_list + raw_code.split('\n')
  return '\n'.join(next_code)


def replace_template_types(raw_code: str, template_types: List[str]) -> str:
  _temp_code = raw_code
  for type in template_types:
    fake_type = get_fake_type(type)
    _temp_code = re.sub(type, fake_type, _temp_code)

  return _temp_code

def remove_stream_names(raw_code: str) -> str:
  """
  to remove the stream name from hls::stream<int> fifo("stream_name");
  make it C compatible
  Should be performed before transforming the templates
  """
  return re.sub(r'(stream[ ]*<.*>[ ]+[a-zA-Z0-9_]+)\(.*\);', r'\1;', raw_code)


def remove_innermost_template_usage(raw_code: str) -> str:
  """
  If the code does not include templates, should return the exact same code
  FIXME: check if any task is templated
  """
  _temp_code = raw_code
  template_types = get_all_template_types(raw_code)

  _temp_code = replace_template_type(_temp_code, template_types)
  _temp_code = add_fake_template_types_def(_temp_code, template_types)
  _temp_code = replace_template_types(_temp_code, template_types)

  return _temp_code


def remove_template_usage(top_func_raw_code: str) -> str:
  # handle nested template types
  code_curr = top_func_raw_code
  count = 0
  while 1:
    code_next = remove_innermost_template_usage(code_curr)
    if code_next == code_curr:
      break
    else:
      count += 1
      code_curr = code_next

    if count > 10:
      assert False, 'looping in template conversion for 10 times, most likely fall into a infinite loop'
  
  return code_curr


def get_top_func_range(raw_code: str, top_name: str) -> Tuple[int, int]:
  
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


def get_top_func(top_path: str, top_name: str) -> str:
  """
  extract the top kernel function from the raw file
  """
  raw_code = open(top_path, 'r').read()
  start_index, end_index = get_top_func_range(raw_code, top_name)
  return raw_code[start_index: end_index+1]


class RevertFakeTypeVisitor(c_ast.NodeVisitor):
  """
  previous we convert all template types to fake types for the cparser
  now we modify the ast to revert the types back
  """
  def __init__(self, ast):
    self.visit(ast)

  def visit_IdentifierType(self, node):
    node.names = list(map(get_orig_type, node.names))


def get_top_ast(top_path: str, top_name: str) -> c_ast.Node:
  _temp_code = get_top_func(top_path, top_name)

  _temp_code = remove_stream_names(_temp_code)
  _temp_code = remove_template_usage(_temp_code)
  
  open('/tmp/tapaconverter_fake_top_func.cpp', 'w').write(_temp_code)
  ast = parse_file('/tmp/tapaconverter_fake_top_func.cpp', use_cpp=True, )
  RevertFakeTypeVisitor(ast)

  return ast