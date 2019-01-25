#!/usr/bin/env python
import sys
import traceback
import os
import logging
import json
import time
import commands
import shutil
import re
import os.path

import ribbonUtils
import globals as GLOBALS

def logStart(msg):
    """
    Param: None
    Desc:  Prints the messages to indicate the start of a particular operation.
    Return: None
    """
    ribbonUtils.logger.info('##################################################################')
    ribbonUtils.logger.info('\t\t' + msg)
    ribbonUtils.logger.info('##################################################################')

def readConfig(config):
        rc = 0
	conf = []
	conf.append('---\n')
        logStart("Read Config file to create the Ansible Var file.")
        configDataJson=ribbonUtils.loadConfigData(config)
        if not configDataJson:
                ribbonUtils.logger.fatal('ConfigData.json not found exiting')
                sys.exit(1)
	print "start"

        configData = json.loads(json.dumps(configDataJson))
	#print configData
	#Validation needs to be done if required. Basic validation is done here.
	sbcIp = configData.get('SBC_IP','')
	clipass = configData.get('SBC_CLI_Passwd','')
	if sbcIp != '' or clipass != '':
		conf.append('SBC_HOST_IP: ' + sbcIp)
		conf.append('SBC_EMA_USER: admin')
		conf.append('SBC_EMA_PASSWD: ' + clipass)
		#Addr_ctxt
		conf.append('SBC_ADDRCNTXT:')
		addctx = configData.get('addressCtxt','')
		addrJson=ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/ADDR_CNTXT.json')
	        if not addrJson:
        	        ribbonUtils.logger.fatal('ADDR_CNTXT.json not found exiting')
                	sys.exit(1)

        	addrData = json.loads(json.dumps(addrJson))
		sonusaddr = addrData.get('sonusAddressContext:addressContext','')
		for x in range(len(addctx)):
			name = addctx[x].get('name','')
			conf.append('  - Name: ' + name )
			addrData['sonusAddressContext:addressContext'][x]['name'] = name
		with open(GLOBALS.GEN_LOC + '/ADDR_CNTXT.json', 'w') as fp:
                	json.dump(addrData, fp, indent=4)
                #changePassword
                clipassdefault = configData.get('SBC_CLI_Passwd_Old','')
                clipassnew = configData.get('SBC_CLI_Passwd','')
                changePasswordJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/changePassword.json')
                if not changePasswordJson:
                        ribbonUtils.logger.fatal('changePassword.json not found exiting')
                        sys.exit(1)

                changePasswordData = json.loads(json.dumps(changePasswordJson))
                if clipassdefault != '' and clipassnew != '' :
                        conf.append('SBC_EMA_PASSWD_DEFAULT: ' + clipassdefault)
                        changePasswordData['input']['oldPassword'] = clipassdefault
                        changePasswordData['input']['newPassword'] = clipassnew
                with open(GLOBALS.GEN_LOC + '/changePassword.json', 'w') as fp:
                        json.dump(changePasswordData, fp, indent=4)
		#Codec Entry
		conf.append('SBC_CodecEntry:')
		codec = configData.get('codecEntry','')
		codecJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/CodecEntry.json')
		if not codecJson:
                        ribbonUtils.logger.fatal('CodecEntry.json not found exiting')
                        sys.exit(1)

                codecData = json.loads(json.dumps(codecJson))
		for x in range(len(codec)):
			name = codec[x].get('name','')
			conf.append('  - Name: ' + name )
			code = codec[x].get('code','')
			conf.append('    codec: ' + code)  
			pktT = codec[x].get('packetsize','')
			conf.append('    packetsize: ' + pktT)
			codecData['sonusCodecEntry:codecEntry'][x]['name'] = name
			codecData['sonusCodecEntry:codecEntry'][x]['codec'] = code
			codecData['sonusCodecEntry:codecEntry'][x]['packetSizeG711'] = pktT
		with open(GLOBALS.GEN_LOC + '/CodecEntry.json', 'w') as fp:
                        json.dump(codecData, fp, indent=4)
		#ingressStaticRoute1
		conf.append('SBC_ingressStaticRoute:')
		ingressStaticRoute = configData.get('ingressStaticRoute','')
		ingressStaticRouteJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/staticRoute_1.json')
		if not ingressStaticRouteJson:
                        ribbonUtils.logger.fatal('staticRoute_1.json not found exiting')
                        sys.exit(1)

                ingressStaticRouteData = json.loads(json.dumps(ingressStaticRouteJson))
		for x in range(len(ingressStaticRoute)):
			ingressdestinationIpAddress = ingressStaticRoute[x].get('ingressdestinationIpAddress','')
			ingressprefix = ingressStaticRoute[x].get('ingressprefix','')
			ingressnextHop = ingressStaticRoute[x].get('ingressnextHop','')
			conf.append('  - destinationIpAddress: ' + ingressdestinationIpAddress)
			conf.append('  - destinationPrefix: ' + ingressprefix )
			conf.append('  - nextHop: ' + ingressnextHop)  
			ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['destinationIpAddress'] = ingressdestinationIpAddress 
			ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['prefix'] = ingressprefix
			ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['nextHop'] = ingressnextHop
		with open(GLOBALS.GEN_LOC + '/staticRoute_1.json', 'w') as fp:
                        json.dump(ingressStaticRouteData, fp, indent=4)
                #ingressStaticRoute2
                conf.append('SBC_ingressStaticRoute:')
                ingressStaticRoute = configData.get('ingressStaticRoute','')
                ingressStaticRouteJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/staticRoute_3.json')
                if not ingressStaticRouteJson:
                        ribbonUtils.logger.fatal('staticRoute_3.json not found exiting')
                        sys.exit(1)

                ingressStaticRouteData = json.loads(json.dumps(ingressStaticRouteJson))
                for x in range(len(ingressStaticRoute)):
                        ingressdestinationIpAddress = ingressStaticRoute[x].get('ingressdestinationIpAddress','')
                        ingressprefix = ingressStaticRoute[x].get('ingressprefix','')
                        ingressnextHop = ingressStaticRoute[x].get('ingressnextHop','')
                        conf.append('  - destinationIpAddress: ' + ingressdestinationIpAddress)
                        conf.append('  - destinationPrefix: ' + ingressprefix )
                        conf.append('  - nextHop: ' + ingressnextHop)
                        ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['destinationIpAddress'] = ingressnextHop
                        ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['prefix'] = 32
                        ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['nextHop'] = ingressdestinationIpAddress
                with open(GLOBALS.GEN_LOC + '/staticRoute_3.json', 'w') as fp:
                        json.dump(ingressStaticRouteData, fp, indent=4)
                #ingressStaticRoute3
                conf.append('SBC_ingressStaticRoute:')
                ingressStaticRoute = configData.get('ingressStaticRoute','')
                ingressStaticRouteJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/staticRoute_5.json')
                if not ingressStaticRouteJson:
                        ribbonUtils.logger.fatal('staticRoute_5.json not found exiting')
                        sys.exit(1)

                ingressStaticRouteData = json.loads(json.dumps(ingressStaticRouteJson))
                for x in range(len(ingressStaticRoute)):
                        ingressdestinationIpAddress = ingressStaticRoute[x].get('ingressdestinationIpAddress','')
                        ingressprefix = ingressStaticRoute[x].get('ingressprefix','')
                        ingressnextHop = ingressStaticRoute[x].get('ingressnextHop','')
                        conf.append('  - destinationIpAddress: ' + ingressdestinationIpAddress)
                        conf.append('  - destinationPrefix: ' + ingressprefix )
                        conf.append('  - nextHop: ' + ingressnextHop)
                        ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['destinationIpAddress'] = "10.100.30.0"
                        ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['prefix'] = 24
                        ingressStaticRouteData['sonusIpInterface:staticRoute'][x]['nextHop'] = ingressnextHop
                with open(GLOBALS.GEN_LOC + '/staticRoute_5.json', 'w') as fp:
                        json.dump(ingressStaticRouteData, fp, indent=4)

		#EgressStaticRoute1
		conf.append('SBC_EgressStaticRoute:')
		egressStaticRoute = configData.get('egressStaticRoute','')
		egressStaticRouteJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/staticRoute_2.json')
		if not egressStaticRouteJson:
                        ribbonUtils.logger.fatal('staticRoute_2.json not found exiting')
                        sys.exit(1)

                egressStaticRouteData = json.loads(json.dumps(egressStaticRouteJson))
		for x in range(len(egressStaticRoute)):
			egressdestinationIpAddress = egressStaticRoute[x].get('egressdestinationIpAddress','')
			egressprefix = egressStaticRoute[x].get('egressprefix','')
			egressnextHop = egressStaticRoute[x].get('egressnextHop','')
			conf.append('  - destinationIpAddress: ' + egressdestinationIpAddress)
			conf.append('  - destinationPrefix: ' + egressprefix )
			conf.append('  - nextHop: ' + egressnextHop)  
			egressStaticRouteData['sonusIpInterface:staticRoute'][x]['destinationIpAddress'] = egressdestinationIpAddress 
			egressStaticRouteData['sonusIpInterface:staticRoute'][x]['prefix'] = egressprefix
			egressStaticRouteData['sonusIpInterface:staticRoute'][x]['nextHop'] = egressnextHop
		with open(GLOBALS.GEN_LOC + '/staticRoute_2.json', 'w') as fp:
                        json.dump(egressStaticRouteData, fp, indent=4)
                #EgressStaticRoute2
                conf.append('SBC_EgressStaticRoute:')
                egressStaticRoute = configData.get('egressStaticRoute','')
                egressStaticRouteJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/staticRoute_4.json')
                if not egressStaticRouteJson:
                        ribbonUtils.logger.fatal('staticRoute_4.json not found exiting')
                        sys.exit(1)

                egressStaticRouteData = json.loads(json.dumps(egressStaticRouteJson))
                for x in range(len(egressStaticRoute)):
                        egressdestinationIpAddress = egressStaticRoute[x].get('egressdestinationIpAddress','')
                        egressprefix = egressStaticRoute[x].get('egressprefix','')
                        egressnextHop = egressStaticRoute[x].get('egressnextHop','')
                        conf.append('  - destinationIpAddress: ' + egressdestinationIpAddress)
                        conf.append('  - destinationPrefix: ' + egressprefix )
                        conf.append('  - nextHop: ' + egressnextHop)
                        egressStaticRouteData['sonusIpInterface:staticRoute'][x]['destinationIpAddress'] = egressnextHop 
                        egressStaticRouteData['sonusIpInterface:staticRoute'][x]['prefix'] = 32
                        egressStaticRouteData['sonusIpInterface:staticRoute'][x]['nextHop'] = egressdestinationIpAddress
                with open(GLOBALS.GEN_LOC + '/staticRoute_4.json', 'w') as fp:
                        json.dump(egressStaticRouteData, fp, indent=4)
                #EgressStaticRoute3
                conf.append('SBC_EgressStaticRoute:')
                egressStaticRoute = configData.get('egressStaticRoute','')
                egressStaticRouteJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/staticRoute_6.json')
                if not egressStaticRouteJson:
                        ribbonUtils.logger.fatal('staticRoute_6.json not found exiting')
                        sys.exit(1)

                egressStaticRouteData = json.loads(json.dumps(egressStaticRouteJson))
                for x in range(len(egressStaticRoute)):
                        egressdestinationIpAddress = egressStaticRoute[x].get('egressdestinationIpAddress','')
                        egressprefix = egressStaticRoute[x].get('egressprefix','')
                        egressnextHop = egressStaticRoute[x].get('egressnextHop','')
                        conf.append('  - destinationIpAddress: ' + egressdestinationIpAddress)
                        conf.append('  - destinationPrefix: ' + egressprefix )
                        conf.append('  - nextHop: ' + egressnextHop)
                        egressStaticRouteData['sonusIpInterface:staticRoute'][x]['destinationIpAddress'] = "10.100.40.0"
                        egressStaticRouteData['sonusIpInterface:staticRoute'][x]['prefix'] = 24
                        egressStaticRouteData['sonusIpInterface:staticRoute'][x]['nextHop'] = egressnextHop
                with open(GLOBALS.GEN_LOC + '/staticRoute_6.json', 'w') as fp:
                        json.dump(egressStaticRouteData, fp, indent=4)
		#ipPeerIpAddress
		ipPeeripAddress = configData.get('ipPeeripAddress','')
		ipPort = configData.get('ipPort','')
                ipPeerJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/ipPeer_2.json')
                if not ipPeerJson:
                        ribbonUtils.logger.fatal('/ipPeer_2.json not found exiting')
                        sys.exit(1)
                ipPeerData = json.loads(json.dumps(ipPeerJson))
                if ipPeeripAddress != '' or ipPort != '':
                        conf.append('ipPeeripAddress: ' + ipPeeripAddress)
                        conf.append('ipPort: ' + ipPort)
                #for x in range(len(ipPeeripAddress)):
                        ipPeerData['sonusIpPeer:ipPeer'][x]['ipAddress'] = ipPeeripAddress
                        ipPeerData['sonusIpPeer:ipPeer'][x]['ipPort'] = ipPort
                with open(GLOBALS.GEN_LOC + '/ipPeer_2.json', 'w') as fp:
                        json.dump(ipPeerData, fp, indent=4)
		#ingressIpPrefix
		conf.append('SBC_ingressIpPrefix:')
		ingressIpPrefix = configData.get('ingressIpPrefix','')
		ingressIpPrefixJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/sipTrunkGroup_1.json')
		if not ingressIpPrefixJson:
                        ribbonUtils.logger.fatal('sipTrunkGroup_1.json not found exiting')
                        sys.exit(1)

                ingressIpPrefixData = json.loads(json.dumps(ingressIpPrefixJson))
		for x in range(len(ingressIpPrefix)):
			ipAddress = ingressIpPrefix[x].get('ipAddress','')
			prefixLength = ingressIpPrefix[x].get('prefixLength','')
			conf.append('  - ipAddress:  '    + ipAddress )
			conf.append('  - prefixLength:  '    + prefixLength )
			ingressIpPrefixData['sonusSipTrunkGroup:sipTrunkGroup']['ingressIpPrefix'][x]['ipAddress'] = ipAddress 
			ingressIpPrefixData['sonusSipTrunkGroup:sipTrunkGroup']['ingressIpPrefix'][x]['prefixLength'] = prefixLength 
		with open(GLOBALS.GEN_LOC + '/sipTrunkGroup_1.json', 'w') as fp:
                        json.dump(ingressIpPrefixData, fp, indent=4)
		#print ingressIpPrefixData
                #egressIpPrefix
                conf.append('SBC_egressIpPrefix:')
                egressIpPrefix = configData.get('egressIpPrefix','')
                egressIpPrefixJson = ribbonUtils.loadConfigData(GLOBALS.PAYLOAD_LOC + '/sipTrunkGroup_2.json')
                if not egressIpPrefixJson:
                        ribbonUtils.logger.fatal('sipTrunkGroup_2.json not found exiting')
                        sys.exit(1)

                egressIpPrefixData = json.loads(json.dumps(egressIpPrefixJson))
                for x in range(len(egressIpPrefix)):
                        ipAddress = egressIpPrefix[x].get('ipAddress','')
                        prefixLength = egressIpPrefix[x].get('prefixLength','')
                        conf.append('  - ipAddress:  '    + ipAddress )
                        conf.append('  - prefixLength:  '    + prefixLength )
                        egressIpPrefixData['sonusSipTrunkGroup:sipTrunkGroup']['ingressIpPrefix'][x]['ipAddress'] = ipAddress
                        egressIpPrefixData['sonusSipTrunkGroup:sipTrunkGroup']['ingressIpPrefix'][x]['prefixLength'] = prefixLength
                with open(GLOBALS.GEN_LOC + '/sipTrunkGroup_2.json', 'w') as fp:
                        json.dump(egressIpPrefixData, fp, indent=4)
                #print egressIpPrefixData

		#EndofParameters
		filename = GLOBALS.VAR_CONF_FILE 
		Conf = open(filename, "w")
		Conf.write("\n".join(conf))
		os.fsync(Conf)
		Conf.close()
		print "Config Gen Done..."	
			
	else:
		ribbonUtils.logger.error('SBC IP and/or CLI Password is invalid')
		rc = 1

	return rc

## Start of main

if sys.argv.__len__() < 2:
    exit(-1)
rc = 1
ribbonUtils.openLog(GLOBALS.LOGGER_NAME, GLOBALS.LOG_FILENAME)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

operations = ['start']
if sys.argv[1] in operations:
	if sys.argv[1] == 'start':
		config = sys.argv[2]
		rc = readConfig(config)
exit(rc)

