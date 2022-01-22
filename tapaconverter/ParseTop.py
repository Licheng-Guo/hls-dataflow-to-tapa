import re

from typing import *
from pycparser import parse_file, c_ast
from tapaconverter.common import get_fake_type


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
  
  return '\n'.join(fake_type_def_list) + '\n\n' + raw_code


def replace_template_types(raw_code: str, template_types: List[str]) -> str:
  _temp_code = raw_code
  for type in template_types:
    fake_type = get_fake_type(type)
    _temp_code = re.sub(type, fake_type, _temp_code)
  
  return _temp_code

def s2s_func_args(raw_code: str) -> str:
  _temp_code = raw_code

  template_types = get_all_template_types(raw_code)
  _temp_code = replace_template_type(_temp_code, template_types)
  _temp_code = add_fake_template_types_def(_temp_code, template_types)
  _temp_code = replace_template_types(_temp_code, template_types)

  return _temp_code


def get_top_ast(top_path: str) -> c_ast.Node:

  raw_code = open(top_path, 'r').read()

  # FIXME: two passes to handle nested template types
  s2s_result = s2s_func_args(raw_code)
  s2s_result = s2s_func_args(s2s_result)

  # parser = c_parser.CParser()
  open('test.cpp', 'w').write(s2s_result)
  ast = parse_file('test.cpp', use_cpp=False, )
  return ast