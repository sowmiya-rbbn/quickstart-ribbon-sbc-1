#!/usr/bin/python

import sys
import traceback
import os
import time
import subprocess
import logging, logging.handlers
import commands
import shutil
import tarfile
import fnmatch
import urllib2
import httplib, socket, ssl
#import pexpect
import requests
import datetime
import json
from ctypes import cdll
import xml.etree.ElementTree as ET
from socket import inet_ntoa
from struct import pack
import fcntl
import struct 
import re
import fileinput
import globals as GLOBALS

sys.path.append('/opt/ribbon/bin/')

DEBUGGING  = False

def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv

def killPid():
    """
    Remove the PID file on exit. Do not let this fail.
    """
    try:
        os.remove(GLOBALS.PID_FILENAME)
    except:
        pass

def pidWarn(function):
    msg = 'Detected PID marker file: ' + GLOBALS.PID_FILENAME + '.  Process already running? '
    print(msg)
    logger.error(msg)
    logger.error(function + ' function not re-issued.')

def openLog(loggerName, fileName=None, fileSize=1000000):
    global logger
    logger = logging.getLogger(loggerName)
    if fileName is not None:
        if DEBUGGING:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        handler   = logging.handlers.RotatingFileHandler(fileName, mode='w', maxBytes=fileSize, backupCount=10, encoding=None, delay=0)
        formatter = timeStampFormatter(fmt='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    else:
        # Redirect the logging output to STDOUT if no log filename is provided.
        logger.setLevel(logging.INFO)
        handler   = logging.StreamHandler(stream=sys.stdout)
        formatter = timeStampFormatter(fmt='%(asctime)s %(levelname)-8s %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class timeStampFormatter(logging.Formatter):
    converter = datetime.datetime.fromtimestamp
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
        return s

def runCmd(c):
    """
    Param: list of strings that describe the
           command to be run.
           e.g. ['service', 'sbx', 'stop']
    Desc:  Method will not return until the
           command has completed.
    Return: Two strings, stderr and stdout which
            were collected from the running
            process.
    """
    logger.debug('runCmd(' + ','.join(c) + ') running...')
    p = subprocess.Popen(c, bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug('runCmd(' + ','.join(c) + ') grabbing output...')
    out, err = p.communicate()
    #logger.debug('err: ' + err)
    #logger.debug('out: ' + out)
    logger.debug('runCmd(' + ','.join(c) + ') finished')
    return out, err, p.returncode

def getPrefix(netMask):
    """
    Param: IPv4 netmask in the form xxx.xxx.xxx.xxx
    Desc:  Converts the netmask to a prefix string
    Return: prefix
    """
    return str(sum([bin(int(x)).count('1') for x in netMask.split('.')]))

def readKeyValPairFile(fileName):
    dict = {}
    with open(fileName) as myfile:
        for line in myfile:
            line = line.rstrip()
            if "=" not in line: continue
            if line.startswith("#"): continue
            line = line.split('#', 1)[0]

            key, val = line.split("=", 1)
            val = val.rstrip()
            dict[key] = val
    return dict


def mustLocate(root, pattern):
    """
    Param:  The directory to look in
            A filename pattern to look for.
    Looks for the occurrence of a single file and throws an exception if said is not found.
    Its up to you to make sure the pattern you supply selects only one file,
    so make the pattern pretty specific
    Return  The name of the file found.
    """
    files = locate(root, pattern)
    try:
        if len(files) != 1:
           raise ValueError('No matching file: ' + pattern)
    except:
        raise ValueError('Error accessing list of downloaded files.')
    return files[0]

def locate(root, pattern):
    """
    Param:  The directory to look in
            The pattern of file names to look for.
    Return: the files matching "pattern" in the dir specified
    """
    files = fnmatch.filter(os.listdir(root), pattern)
    return files

def loadConfigData(fileName=GLOBALS.CONFIG_DATA_FILE):
    data = {}
    content = ''
    if not os.path.exists(fileName):
        logger.warn('Missing json file: ' + str(fileName))
        return data

    try:
        with open(fileName) as dataFile:
            content = dataFile.read()
    except Exception as e:
        logger.warn('Exception while reading file: ' + fileName + ', exception: ' + str(e))
        return data
    try:
        data = json.loads(json.dumps(json.loads(content, object_hook=_decode_dict)))
    except ValueError:
        logger.warn('Content does not appear to be properly formed Json. fileName: ' + fileName)
    except Exception as e:
        logger.warn('Exception while decoding json file: ' + fileName + ', exception: ' + str(e))
    return data

def validateIPv4(address, addressType):

    # If prefix information is there in the IP, remove it and validate only the IP address
    if address.find('/') >= 0:
        isValidPrefix = validatePrefix(address, "V4")
        if isValidPrefix:
            address = address.split('/')[0]
        else:
            logger.error("Invalid IPV4 Prefix found with IP address. Value: " + str(address))
            return False
    try :
        socket.inet_pton(socket.AF_INET, address)
    except socket.error:  # not a valid address
        logger.error('ValidateIPv4 error for addressType : ' + addressType + ' , Invalid.  Address : ' + str(address))
        return False
    except Exception as e:
        logger.error('ValidateIPv4 error:' + str(e.message) + ' Address : ' + str(address))
        return False
    return True

def validateIPv6(address, addressType):

    # If prefix information is there in the IP, remove it and validate only the IP address
    if address.find('/') >= 0:
        isValidPrefix = validatePrefix(address, "V6")
        if isValidPrefix:
            address = address.split('/')[0]
        else:
            logger.error("Invalid IPV6 Prefix found with IP address. Value: " + str(address))
            return False
    #logger.info("validateIPv6 : address :" + str(address))

    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:  # not a valid address
        logger.error('ValidateIPv6 error for addressType : ' + addressType + ' , Invalid. Address : ' + str(address))
        return False
    except Exception as e:
        logger.error('ValidateIPv6 error:' + str(e.message)+ ' Address : ' + str(address))
        return False

    return True

def getIpVersion(address):
    """
    Input Param : IP address.
    Output Param: IP address version.
                  Returns 0 if IP address is invalid.
                  Returns 4/6 if IP address is V4/V6 respectively.
    """

    ipVersion = 0

    try:
        socket.inet_pton(socket.AF_INET, address)
        ipVersion = 4
    except:
        pass

    try:
        socket.inet_pton(socket.AF_INET6, address)
        ipVersion = 6
    except:
        pass

    return ipVersion

def validatePrefix(address, type):
    """
    Input Params :
    1. address : Can be address or prefix value.
    2. IP version : V4 or V6
    """

    # Check if the prefix information is present in the IP field.
    if address.find('/') >= 0:
        prefix = address.split('/')[1]
    else:
        # Will consider the scenario where prefix is passed directly
        prefix = address

    if prefix.isdigit():
        if type == "V4":
            if int(prefix) >= 0 and int(prefix) <=32:
                return True
        if type == "V6":
            if int(prefix) >= 0 and int(prefix) <=128:
                return True
    logger.error('validatePrefix: Error for prefix Invalid. Value: ' + str(address))
    return False

def parse_cpu_spec(spec):
    """Parse a CPU set specification.

    :param spec: cpu set string eg "1-4,^3,6"

    Each element in the list is either a single
    CPU number, a range of CPU numbers, or a
    caret followed by a CPU number to be excluded
    from a previous range.

    :returns: a set of CPU indexes
    """

    cpuset_ids = set()
    cpuset_reject_ids = set()
    for rule in spec.split(','):
        rule = rule.strip()
        # Handle multi ','
        if len(rule) < 1:
            continue
        # Note the count limit in the .split() call
        range_parts = rule.split('-', 1)
        if len(range_parts) > 1:
            reject = False
            if range_parts[0] and range_parts[0][0] == '^':
                reject = True
                range_parts[0] = str(range_parts[0][1:])

            # So, this was a range; start by converting the parts to ints
            try:
                start, end = [int(p.strip()) for p in range_parts]
            except ValueError:
                raise exception.Invalid(_("Invalid range expression %r")
                                        % rule)
            # Make sure it's a valid range
            if start > end:
                raise exception.Invalid(_("Invalid range expression %r")
                                        % rule)
            # Add available CPU ids to set
            if not reject:
                cpuset_ids |= set(range(start, end + 1))
            else:
                cpuset_reject_ids |= set(range(start, end + 1))
        elif rule[0] == '^':
            # Not a range, the rule is an exclusion rule; convert to int
            try:
                cpuset_reject_ids.add(int(rule[1:].strip()))
            except ValueError:
                raise exception.Invalid(_("Invalid exclusion "
                                          "expression %r") % rule)
        else:
            # OK, a single CPU to include; convert to int
            try:
                cpuset_ids.add(int(rule))
            except ValueError:
                raise exception.Invalid(_("Invalid inclusion "
                                          "expression %r") % rule)

    # Use sets to handle the exclusion rules for us
    cpuset_ids -= cpuset_reject_ids

    return cpuset_ids

def cidr(prefix):
    return socket.inet_ntoa(struct.pack(">I", (0xffffffff << (32 - prefix)) & 0xffffffff))

