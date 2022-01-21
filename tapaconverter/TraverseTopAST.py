from typing import *
from pycparser import c_ast, c_generator

generator = c_generator.CGenerator()


class Task:
  def __init__(self, task_name: str, arg_list: List[str]):
    self.task_name = task_name
    self.arg_list = arg_list


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

def get_all_tasks(ast: c_ast.Node):
  get_task_visitor = GetTaskVisitor()
  get_task_visitor.visit(ast)
  get_task_visitor.dump_task_invoke()
