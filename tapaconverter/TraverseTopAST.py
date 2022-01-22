import re
import logging

from typing import *
from pycparser import c_ast, c_generator

generator = c_generator.CGenerator()


class Task:
  def __init__(self, task_name: str, arg_list: List[str]):
    self.task_name = task_name
    self.arg_list = arg_list


class Stream:
  def __init__(self, name: str, depth: str, type: str):
    self.name = name
    self.depth = depth
    self.type = type

  def get_tapa_stream(self):
    return f'tapa::stream<{self.type}, {self.depth}> {self.name};'


class Pragma:
  def __init__(self, pragma_raw: str):
    # remove spaces before and after '='
    pragma_raw = re.sub('[ ]*=[ ]*', '=', pragma_raw)
    items = pragma_raw.split(' ')

    if items[0].upper() != 'HLS':
      logging.error(f'cannot parse pragma {pragma_raw}')
      raise NotImplementedError

    self.pragma_raw = pragma_raw
    self.name = items[1].lower()
    self.kv_properties = {}
    self.single_properties = []

    for item in items[2:] :
      if '=' in item:
        k, v = item.split('=')
        self.kv_properties[k] = v
      else:
        self.single_properties.append(item)

  def show(self):
    print(self.pragma_raw)


class GetTaskVisitor(c_ast.NodeVisitor):
  def __init__(self):
    self.task_list:  List[Task] = []

  def visit_FuncCall(self, node):
    task_name = node.name.name
    arg_list = [generator.visit(arg) for arg in node.args.exprs]
    self.task_list.append(Task(task_name, arg_list))

  def dump_task_invoke(self):
    buf = []
    buf.append(f'tapa::task()')
    for task in self.task_list:
      buf.append(f'  .invoke({task.task_name}, ')
      for arg in task.arg_list:
        buf.append(f'          {arg},')
      buf[-1] = buf[-1].replace(',', ')')
    buf.append('  ;')
    print('\n'.join(buf))


class GetPragmaVisitor(c_ast.NodeVisitor):
  def __init__(self):
    self.pragma_list: List[Pragma] = []

  def visit_Pragma(self, node):
    self.pragma_list.append(Pragma(node.string))

  def show_all(self):
    for pragma in self.pragma_list:
      pragma.show()

  def get_streams(self) -> List[Stream]:
    stream_list = []
    for pragma in self.pragma_list:
      if pragma.name == 'stream':
        s = Stream(pragma.kv_properties['variable'], pragma.kv_properties['depth'], 'none_type')
        stream_list.append(s)

    return stream_list


def get_all_tasks(ast: c_ast.FileAST):
  get_task_visitor = GetTaskVisitor()
  get_task_visitor.visit(ast)
  get_task_visitor.dump_task_invoke()


def get_stream_depth(ast: c_ast.FileAST):
  get_pragma_visitor = GetPragmaVisitor()
  get_pragma_visitor.visit(ast)
  stream_list = get_pragma_visitor.get_streams()
  for s in stream_list:
    print(s.get_tapa_stream())
