import argparse

from tapaconverter.ParseTop import get_top_ast
from tapaconverter.TraverseTopAST import get_all_tasks, get_stream_depth


if __name__ == '__main__':
  parser = argparse.ArgumentParser()  
  parser.add_argument('--filename', type=str, required=True)
  args = parser.parse_args()

  ast = get_top_ast(args.filename)
  get_stream_depth(ast)
  get_all_tasks(ast)
