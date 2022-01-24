import argparse

from tapaconverter.ParseTop import get_top_ast
from tapaconverter.TraverseTopAST import *


if __name__ == '__main__':
  parser = argparse.ArgumentParser()  
  parser.add_argument('--filename', type=str, required=True)
  parser.add_argument('--top_name', type=str, required=True )
  args = parser.parse_args()

  ast = get_top_ast(args.filename, args.top_name)
  # ast.show()
  get_tapa_top_header(ast)
  get_all_streams(ast)
  get_all_tasks(ast)
