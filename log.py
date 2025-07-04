

def log(line: str, path: str = 'log.txt') -> None:
  print(line)
  with open(f'logs/{path}', 'a') as f:
    f.write(line)

