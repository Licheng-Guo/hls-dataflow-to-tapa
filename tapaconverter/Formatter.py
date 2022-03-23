import os
import re

def format_output(filename):
  options = [
    "--delete-empty-lines",
    "--align-reference=type",
    "--align-pointer=type",
    "--convert-tabs",
    "--unpad-paren",
    "--pad-paren-in",
  ]
  command = 'astyle ' + ' '.join(options) + ' ' + filename
  os.system(command)
  os.system(f'rm {filename}.orig')

  contents = open(filename, 'r').read()
  
  # remove extra spaces
  while 1:
    contents, update_num = re.subn('(\S ) ', '$1', contents)
    if update_num == 0:
      break
  
  # remove extra empty lines
  while 1:
    contents, update_num = re.subn(r'\n\n\n', r'\n\n', contents)
    if update_num == 0:
      break
  
  open(filename, 'w').write(contents)