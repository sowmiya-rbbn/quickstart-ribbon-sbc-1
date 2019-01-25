#!/usr/bin/env python
import os
import os.path

cwd = os.getcwd()
print(cwd)
Pdir = os.path.abspath(os.path.join(cwd, os.pardir))
                        
LOG_FILENAME                   =  Pdir+'/ConfigGen.log'
LOGGER_NAME                    = 'ConfigGen'
CONFIG_DATA_FILE	       = '/root.input.json'
VAR_CONF_FILE		       = Pdir+'/vars/gen.yml'
PAYLOAD_LOC		       = Pdir+'/payload'
GEN_LOC			       = Pdir+'/payload'


