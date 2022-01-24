import re
import logging

from typing import *
from pycparser import c_ast, c_generator
from tapaconverter.ParseTop import get_top_ast

generator = c_generator.CGenerator()

__all__ = [
  'get_all_streams',
  'get_all_tasks',
  'get_tapa_top_header',
]


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
  """
  data structure to record the pragmas
  """
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
  """
  extract all tasks
  """
  def __init__(self):
    self.task_list:  List[Task] = []

  def visit_FuncCall(self, node):
    task_name = node.name.name
    arg_list = [generator.visit(arg) for arg in node.args.exprs]
    self.task_list.append(Task(task_name, arg_list))

  def dump_task_invoke(self) -> str:
    buf = []
    buf.append(f'tapa::task()')
    for task in self.task_list:
      buf.append(f'  .invoke({task.task_name}, ')
      for arg in task.arg_list:
        buf.append(f'          {arg},')
      buf[-1] = buf[-1].replace(',', ')')
    buf.append('  ;')
    return '\n'.join(buf) + '\n'


class GetPragmaVisitor(c_ast.NodeVisitor):
  """
  extract the depth of streams
  """
  def __init__(self, ast):
    self.pragma_list: List[Pragma] = []
    self.visit(ast)

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


class GetStreamVisitor(c_ast.NodeVisitor):
  def __init__(self, ast):
    self.stream_to_type = {}
    self.visit(ast)

  def visit_FuncDecl(self, node):
    """
    avoid visiting the decl nodes within a FuncDecl node
    """
    return

  def visit_TypeDecl(self, node):
    """
    extract the type of stream declarations
    """
    if isinstance(node.type, c_ast.IdentifierType):
      orig_type = node.type.names[0]
      stream_match = re.search(r'stream<(.*)>', orig_type)
      if stream_match:
        stream_type = stream_match.group(1).strip()
        self.stream_to_type[node.declname] = stream_type


class GetTapaFuncDefVisitor(c_ast.NodeVisitor):
  """
  transform the pointer parameters to tapa::mmap<> parameters
  """
  def __init__(self, ast: c_ast.ParamList):
    self.is_top_func_decl_children = False
    self.top_name = None
    self.top_type = None
    self.tapa_param_list = None
    self.visit(ast)

  def _visit_children(self, node):
    for c in node:
      self.visit(c)

  def visit_ParamList(self, node):
    """
    set a mark so that children visit knows we are under a param list
    """
    self.is_top_func_decl_children = True
    self._visit_children(node)
    self.is_top_func_decl_children = False

    self.tapa_param_list = generator.visit(node)

  def visit_Decl(self, node):
    """
    since we need to modify a PtrDecl node in the ast, we need to visit the upper level Decl
    """
    if self.is_top_func_decl_children:
      if isinstance(node.type, c_ast.PtrDecl):
        node.type = node.type.type
        node.type.type.names = [f'tapa::mmap<{n} >' for n in node.type.type.names]
        return

    self._visit_children(node)

  def visit_FuncDecl(self, node):
    """
    record the top name and type
    """
    self.top_name = node.type.declname
    self.top_type = node.type.type.names[0]

    self._visit_children(node)

  def get_tapa_top(self):
    tapa_top = []
    
    tapa_top.append(f'{self.top_type} {self.top_name} (')
    tapa_params_split = self.tapa_param_list.split(',')
    tapa_top += [f'    {param.strip()},' for param in tapa_params_split]
    tapa_top[-1] = tapa_top[-1].replace(',', '')
    tapa_top.append(')') 
    return '\n'.join(tapa_top)


def get_all_tasks(ast: c_ast.FileAST):
  get_task_visitor = GetTaskVisitor()
  get_task_visitor.visit(ast)
  return get_task_visitor.dump_task_invoke()


def get_all_streams(ast: c_ast.FileAST) -> str:
  get_pragma_visitor = GetPragmaVisitor(ast)
  stream_list = get_pragma_visitor.get_streams()

  get_stream_visitor = GetStreamVisitor(ast)

  stream_def_list = []
  for s in stream_list:
    s.type = get_stream_visitor.stream_to_type[s.name]
    stream_def_list.append(s.get_tapa_stream() + '\n')
  return ''.join(stream_def_list)


def get_tapa_top_header(ast: c_ast.FileAST) -> str:
  return GetTapaFuncDefVisitor(ast).get_tapa_top()


def get_tapa_top(top_path, top_name) -> str:
  ast = get_top_ast(top_path, top_name)
  header = get_tapa_top_header(ast)
  stream_def = get_all_streams(ast)
  task_def = get_all_tasks(ast)

  return f'{header} {{\n{stream_def}\n{task_def}}}'