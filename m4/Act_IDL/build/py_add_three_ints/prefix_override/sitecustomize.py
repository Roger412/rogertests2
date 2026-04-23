import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/roger/Github/rogertests2/m4/Act_IDL/install/py_add_three_ints'
