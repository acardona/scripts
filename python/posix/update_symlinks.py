# Albert Cardona 2019-05-14
# A script to update any symbolic link under a defined directory ('top_folder')
# and its nested subdirectories to a defined file ('redirect_target').

import os, sys

if len(sys.argv) < 3:
  print("usage: python update_symlinks.py /path/to/top-level-folder /path/to/redirect_target.jpg <skip-if-os.readlink-fails-to-match>")
  sys.exit(0)

top_folder = sys.argv[1]
if not os.path.exists(top_folder) or not os.path.isdir(top_folder):
  print("Not a directory or doesn't exist: " + top_folder)
  sys.exit(0)

redirect_target = sys.argv[2]
if not os.path.exists(redirect_target):
  print("Doesn't exist: " + redirect_target)
  option = input("Continue anyway? [y/N]: ")
  if not option.startswith('y'):
    sys.exit(0)

# A substring in the resolved path of the symlink to replace
match_string = sys.argv[3] if len(sys.argv) > 3 else None

count = 0

for root, folders, filenames in os.walk(top_folder):
  print("At folder: " + root)
  for filename in filenames:
    path = os.path.join(root, filename)
    if os.path.islink(path):
      if match_string and -1 == os.readlink(path).find(match_string):
        continue
      # Would work too, but can't overwrite existing symlink
      #os.remove(path)
      #os.symlink(redirect_target, path)
      # Less ops: emit a command instead:
      command = "ln -sf %s %s" % (redirect_target, path)
      print("Will run: " + command)
      if 0 != os.system(command):
        print("FAILED: " + command)
      count += 1

os.sync()

print("Updated %i symlinks" % count)

