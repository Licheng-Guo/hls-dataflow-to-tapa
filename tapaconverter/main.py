import argparse

from tapaconverter.common import TEMP_FILE_PATH
from tapaconverter.TraverseTopAST import get_tapa_init_version
from tapaconverter.UpdateStreamDirection import update_stream_directions

if __name__ == '__main__':
  parser = argparse.ArgumentParser()  
  parser.add_argument('--filename', type=str, required=True)
  parser.add_argument('--top_name', type=str, required=True)
  parser.add_argument('--output', type=str, required=True)
  args = parser.parse_args()

  tapa_cpp = get_tapa_init_version(args.filename, args.top_name)

  open(TEMP_FILE_PATH, 'w').write(tapa_cpp)
  tapa_cpp = update_stream_directions(TEMP_FILE_PATH, args.top_name)

  open(args.output, 'w').write(tapa_cpp)