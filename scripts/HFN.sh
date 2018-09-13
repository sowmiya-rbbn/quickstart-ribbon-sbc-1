#!/bin/bash

#############################################################
#
# Copyright (c) 2018 Sonus Networks, Inc.
#
# All Rights Reserved.
# Confidential and Proprietary.
#
# HFN.sh
#
# Lokesh Ranadive
# 4/1/2018
#
# Module Description:
# Script to enable HFN(HA forwarding node) instance as frontend for public facing 
# PKT port of SBC.
# The script will perform the following steps when called from cloud-init (setup function):
# 1) Save old iptables rules : preConfigure
# 2) Enalbe IP Forwarding :configureNATRules
# 3) Read Secondary IPs of SBC, IP of machine for which we need route table
# entry(for ssh connection). Route for REMOTE_SSH_MACHINE_IP is set so that user
# can connect HFN instance over eth1 : readConfig.
# Route entry for all SIPs of SBC(pkt0) are set to route packets towards SBC via
# eth2
# 4) Setup DNAT for incoming traffic over eth0 (public facing EIPs for SBC's pkt
# port) and forward it to SBC's secondary IPs over eth2 : configureNATRules
# 5) Setup SNAT for traffic coming from SBC and forward it to public
# end-points over eth0 (EIPs) : configureNATRules
# 6) Configure route for IP of machine read in step #3(REMOTE_SSH_MACHINE_IP) : configureMgmtNAT
# 7) Log applied iptables configuration and route: showCurrentConfig 
#
#
# For debugging-
# Call HFN.sh with cleanup switch. e.g sh HFN.sh cleanup:
# 1) Remove all routes set to forward SBC SIPs(pkt0)
# 2) Save iptable entries 
# 3) Flush iptables
# This option is useful to debug connectivity of end-point with HFN, after
# calling this no packet is forwarded to SBC, user can ping all EIPs on eth0 to
# make sure connectivity between end-point and HFN is working fine.
# Once this is done user MUST reboot HFN node to restore all forwarding rules
# and routes.
# 
#
# NOTE: This script is run by cloud-init in HFN instance.
#
# This script should be uploaded to S3 bucket and
# AWS_HFN_HA_template_auto_subnet.json configures HFN instance to
# get this script from S3 bucket and run with cloud-init.
#
#
#############################################################


## This version is changed to current release build by build process.
TemplateVersion="TEMPLATE_VERSION_UNKNOWN"
HFNRoot="/home/ec2-user/HFN"
varFile="$HFNRoot/natVars.input"
logFile="$HFNRoot/HFN.log"
oldRules="$HFNRoot/iptables.rules.prev"

PROG=${0##*/}

usage()
{
    echo $1
    echo "usage: $PROG <setup|cleanup>"
    echo "Example:"
    echo "$PROG setup"
    exit
}

timestamp()
{
 date +"%Y-%m-%d %T"
}

doneMessage()
{
    echo $(timestamp) " =========================    DONE HFN.sh     =========================================="
    echo $(timestamp) ""
    echo $(timestamp) ""
    exit 
}

errorAndExit()
{
    echo $(timestamp) " Error: $1"
    doneMessage
}


saveAndClearOldRules()
{
    sudo iptables-save > $oldRules
    if [ "$?" = "0" ]; then
        echo $(timestamp) " Clean all old firewall rules"
        iptables -X
        iptables -t nat -F
        iptables -t nat -X
        iptables -t mangle -F
        iptables -t mangle -X
        iptables -P INPUT ACCEPT
        iptables -P FORWARD ACCEPT
        iptables -P OUTPUT ACCEPT
    else
        errorAndExit "Cound not save old iptables rules. Exiting"
    fi
}


getRegion()
{
    # Get region.
    availZone=`curl -s "http://169.254.169.254/latest/meta-data/placement/availability-zone"`
    if [[ -z "$availZone" ]];then
        errorAndExit "Failed to get availability-zone."
    fi
    
    region="${availZone::-1}"
    echo "$region"
}

getSWePkt0CIDR()
{
    local region=""
    
    # Get region.
    region=$(getRegion)
    if [[ -z "$region" ]];then
        errorAndExit "Failed to get region."
    fi
   
    # Get subnet-id for SECONDARY_IP_OF_SBC.
    sbcPkt0SubnetId=`aws ec2 describe-network-interfaces --filters "Name=addresses.private-ip-address,Values=$SBC_SECONDARY_IP" --region $region | grep SubnetId | awk -F ":" '{print $2}' | awk -F "\"" '{print $2}'`
    if [[ -z "$sbcPkt0SubnetId" ]];then
        errorAndExit "Failed to get SBC Pkt0 subnet Id."
    fi

    # Get CIDR for SECONDARY_IP_OF_SBC.
    sbcPkt0CIDR=`aws ec2 describe-subnets --subnet-ids $sbcPkt0SubnetId --region $region | grep "CidrBlock\":" | awk -F ":" '{print $2}' | awk -F "\"" '{print $2}'`
    if [[ -z "$sbcPkt0CIDR" ]];then
        errorAndExit "Failed to get SBC Pkt0 CIDR."
    fi

    echo "$sbcPkt0CIDR"
}


routeCleanUp()
{
    echo $(timestamp) " Route clean up for SWe Pkt0 secondary IPs and remote machine's public IP."

    local sbcPkt0CIDR=""
    sbcPkt0CIDR=$(getSWePkt0CIDR)
    if [[ -z "$sbcPkt0CIDR" ]];then
        errorAndExit " Failed to get SWe Pkt0 CIDR."
    fi
  
    ip route | grep -E "$sbcPkt0CIDR.*$ETH2_GW.*eth2"
    if [ "$?" = "0" ]; then
        #route del -net <CIDR> gw <GW_OF_ETH2> dev eth2
        route del -net $sbcPkt0CIDR gw $ETH2_GW dev eth2
        if [ "$?" = "0" ]; then
            echo $(timestamp) " Route deleted to reach SBC Pkt0 CIDR $sbcPkt0CIDR from eth2"
        else
            errorAndExit " Failed to delete route to reach SBC CIDR $sbcPkt0CIDR from eth2"
        fi
    else
        echo $(timestamp) " Route not available to reach SBC Pkt0 CIDR $sbcPkt0CIDR from eth2"
    fi

    ip route | grep -E "$REMOTE_SSH_MACHINE_IP.*$ETH1_GW.*eth1"
    if [ "$?" = "0" ]; then
        #route del <PUBLIC_IP_OF_MACHINE_USED_TO_MANAGE_HFN> gw <GW_OF_ETH0> dev eth1
        route del $REMOTE_SSH_MACHINE_IP gw $ETH1_GW dev eth1
        if [ "$?" = "0" ]; then
            echo $(timestamp) " Route deleted for remote machine's public IP($REMOTE_SSH_MACHINE_IP) to reach from eth1"
        else
            errorAndExit " Failed to delete route for remote machine's public IP($REMOTE_SSH_MACHINE_IP) to reach from eth1"
        fi
    else
        echo $(timestamp) " Route not available for remote machine's public IP($REMOTE_SSH_MACHINE_IP) to reach from eth1"
    fi
}


preConfigure()
{
    ### Redirect all echo $(timestamp) to file after writing ip_forward
    exec >> $logFile 2>&1
    echo $(timestamp) " ==========================   Starting HFN.sh  ============================"
    echo $(timestamp) " Enabled IP forwarding"
    echo $(timestamp) " This script will setup DNAT, SNAT and IP forwarding."
    echo $(timestamp) " Save old rules in $HFNRoot/firewall.rules"
    saveAndClearOldRules
}



readConfig()
{
    echo $(timestamp) " Read variables from file $varFile"

    source $varFile
    echo $(timestamp) " Data from $varFile:"
    echo $(timestamp) " SBC_SECONDARY_IP $SBC_SECONDARY_IP"
    echo $(timestamp) " REMOTE_SSH_MACHINE_IP       $REMOTE_SSH_MACHINE_IP"
    echo $(timestamp) ""

    ETH1_GW=`/sbin/ip route | grep eth1|  awk '/default/ { print $3 }'`
    ETH2_GW=`/sbin/ip route | grep eth2|  awk '/default/ { print $3 }'`

    echo $(timestamp) ""
    echo $(timestamp) " Default GWs:"
    echo $(timestamp) " ETH2_GW          $ETH2_GW"
    echo $(timestamp) " ETH1_GW          $ETH1_GW"
}

installConntrack()
{
    echo $(timestamp) " Check and install conntrack "
    rpm -q conntrack-tools
    installed=$?

    if [ $installed -eq 0 ];then
        echo $(timestamp) " conntrack already installed."
    else
        echo $(timestamp) " conntrack is not installed. Installing it."
        yum -y install conntrack
    fi

    rpm -q conntrack-tools
    installed=$?

    if [ $installed -eq 0 ];then
        echo $(timestamp) " conntrack installed."
    else
        errorAndExit "Could not install conntrack. Exit."
    fi
}

configureNATRules()
{
    echo $(timestamp) " ==========================   Section 1 ============================"
    echo $(timestamp) " Endpoint -> EIP of HFN instance (eth0) -> eth2 -> VPC router -> SBC"
    echo $(timestamp) " This setting enables HFN instance to forward all packets received on eth0[EIP] to SBC's(current active) secondary IP."
    echo $(timestamp) " These packets are sent out on eth2 interface and routed via private VPC's default routing table rule"
    echo $(timestamp) " ==================================================================="
    echo $(timestamp) ""
    echo $(timestamp) ""
    
    local sbcPkt0CIDR=""

    iptables -A FORWARD -i eth0 -o eth2 -j ACCEPT
    if [ "$?" = "0" ]; then
        echo $(timestamp) " Set Forward ACCEPT rule all packets coming from outside eth0 to eth2 towards SBC"
    else
        errorAndExit "Failed to set forward ACCEPT rule for all packets coming on EIP(eth0)"
    fi
    
    # Get number of secondary IP assigned on HFN eth0 interface.
    secIpOnHfnEth0Count="${#secIpOnHfnEth0SortArr[@]}"

    # Get number of secondary IP assigned on SBC Pkt0 interface.
    secIpOnSWePkt0Count="${#secIpOnSWePkt0SortArr[@]}"

    addNumRoute=$(( secIpOnHfnEth0Count < secIpOnSWePkt0Count ? secIpOnHfnEth0Count : secIpOnSWePkt0Count ))
    # Get SBC Pkt0 CIDR.
    sbcPkt0CIDR=$(getSWePkt0CIDR)
    if [[ -z "$sbcPkt0CIDR" ]];then
        errorAndExit "Failed to get SWe Pkt0 CIDR."
    fi
   
    ip route | grep -E "$sbcPkt0CIDR.*$ETH2_GW.*eth2"
    if [ "$?" = "0" ]; then
        echo $(timestamp) " Route is already available to reach SBC Pkt0 CIDR  $sbcPkt0CIDR from eth2"
    else
        #route add -net <CIDR> gw <GW_OF_ETH2> dev eth2
        route add -net $sbcPkt0CIDR gw $ETH2_GW dev eth2
        if [ "$?" = "0" ]; then
            echo $(timestamp) " Set route to reach SBC Pkt0 CIDR  $sbcPkt0CIDR from eth2"
        else
            errorAndExit "Failed to set route to reach SBC CIDR  $sbcPkt0CIDR from eth2"
        fi
    fi
        
    for (( idx=0; idx<$addNumRoute; idx++ ))
    do
        #iptables -t nat -A PREROUTING  -i eth0 -d <DESTINATION_IP> -j DNAT --to <SECONDARY_IP_OF_SBC>
        iptables -t nat -A PREROUTING  -i eth0 -d ${secIpOnHfnEth0SortArr[$idx]} -j DNAT --to ${secIpOnSWePkt0SortArr[$idx]}
        if [ "$?" = "0" ]; then
            echo $(timestamp) " Set up proper DNAT for destination IP ${secIpOnHfnEth0SortArr[$idx]} to offset ${secIpOnSWePkt0SortArr[$idx]} "
        else
            errorAndExit "Failed to set DNAT rule for destination IP ${secIpOnHfnEth0SortArr[$idx]} to offset ${secIpOnSWePkt0SortArr[$idx]}."
        fi
    done

    ## Reset connection tracking
    ## Any packet received on eth0 before NAT rules are set are not forwarded
    ## to sbc via eth2, connection tracking will not forward those packets even
    ## if NAT rules are set after receiving first packet from that source
    ## IP/Port as it has cache entry for source IP and Port.
    ## Reset connection tracking will treat them as new stream and those packets
    ## will be forwarded to SBC via eth2 once SNAT and DNAT rules are setup
    ## properly.

    installConntrack

    conntrack -F conntrack
    if [ "$?" = "0" ]; then
        echo $(timestamp) " Flushing connection tracking rules."
    else
        echo $(timestamp) " (WARNING):Flushing connection tracking rules failed."
    fi


    echo $(timestamp) " ==========================   Section 2 ============================"
    echo $(timestamp) " This configuration is needed for calls originated by SBC on public IP (using EIP of HFN)"
    echo $(timestamp) " SBC -> routing table -> eth1 (HFN instance) -> DNAT -> eth0 -> EIP "
    echo $(timestamp) " This setting enables HFN instance to forward all packets received on eth2 from SBC's(current active) secondary IP."
    echo $(timestamp) " These packets are sent out on eth0 interface as default route is set for this interface and routed via default rule of routing table"
    echo $(timestamp) " Private subnet should use rules like following to route all packets to HFN instance-"
    echo $(timestamp) "


    #### Use routing table to route packets from pkt0 to reach eth2 of HFN instance

    Route Table:
    rtb-XXXXXXXXXXXXXXXX | PRIVATE_SUBNET_NAT_ROUTING_TABLE
    Destination      Target
    10.54.0.0/16     local
    0.0.0.0/0        eni-014b69a1554d886c0 / i-0e9006e91b9fbc3fa

    "

    iptables -A FORWARD -i eth2 -o eth0 -j ACCEPT
    if [ "$?" = "0" ]; then
        echo $(timestamp) " Set Forward ACCEPT rule all packets coming from SBC (eth2) to eth0"
    else
        errorAndExit "Failed to set ACCEPT rule all packets coming from SBC (eth2) to eth0"
    fi


    for (( idx=0; idx<$addNumRoute; idx++ ))
    do
        iptables -t nat -I POSTROUTING -o eth0 -s ${secIpOnSWePkt0SortArr[$idx]} -j SNAT --to ${secIpOnHfnEth0SortArr[$idx]}  
        if [ "$?" = "0" ]; then
            echo $(timestamp) " Set up POSTROUTING rule (source IP ${secIpOnSWePkt0SortArr[$idx]}, to offset ${secIpOnHfnEth0SortArr[$idx]}) for packet sent on eth0 "
        else
            errorAndExit "Failed to set POSTROUTING rule (source IP ${secIpOnSWePkt0SortArr[$idx]}, to offset ${secIpOnHfnEth0SortArr[$idx]}) for packet sent on eth0"
        fi
    done

    echo $(timestamp) " ==================================================================="
    echo $(timestamp) ""
    echo $(timestamp) ""

}

configureMgmtNAT()
{
    echo $(timestamp) " ==========================   Section 3 ============================"
    echo $(timestamp) " Optional configuration to reach eth1 using EIP. "


    if [ -z "${REMOTE_SSH_MACHINE_IP}" ]; then
        echo $(timestamp) " No IP is given for REMOTE_SSH_MACHINE_IP field, no route is set for managing this instance over eth1."
    else
        echo $(timestamp) " eth1 is used to manage this HFN instance, we can login using private IP to manage HFN machine without setting default route"
        echo $(timestamp) " default route points to eth0 which will be used to interface all traffic for SBC"

        ip route | grep -E "$REMOTE_SSH_MACHINE_IP.*$ETH1_GW.*eth1"
        if [ "$?" = "0" ]; then
            echo $(timestamp) " Route is already available for remote machine's public IP($REMOTE_SSH_MACHINE_IP), from this IP you can SSH to HFN over EIP(eth1)"
        else
            #route add <PUBLIC_IP_OF_MACHINE_USED_TO_MANAGE_HFN> gw <GW_OF_ETH0> dev eth1
            route add $REMOTE_SSH_MACHINE_IP gw $ETH1_GW dev eth1
            if [ "$?" = "0" ]; then
                echo $(timestamp) " Route added for remote machine's public IP($REMOTE_SSH_MACHINE_IP), from this IP you can SSH to HFN over EIP(eth1)"
            else
                errorAndExit "Failed to add route for ($REMOTE_SSH_MACHINE_IP)"
            fi
        fi
    fi
    echo $(timestamp) " ==================================================================="
    echo $(timestamp) ""
    echo $(timestamp) ""
}

showCurrentConfig()
{
    echo $(timestamp) " ==========================   Section 3 ============================"
    echo $(timestamp) " Applied iptable rules and kernel routing table. "
    natTable=`iptables -t nat -vnL`
    echo " "
    echo $(timestamp) " NAT tables:"
    echo $(timestamp) " $natTable "

    filterTable=`iptables -t filter -vnL`
    echo " "
    echo $(timestamp) " Filter tables:"
    echo $(timestamp) " $filterTable "

    echo " "
    routeOutput=`route -n`
    echo $(timestamp) " Route:"
    echo $(timestamp) " $routeOutput "
    echo " "

    echo $(timestamp) " ==================================================================="
    echo $(timestamp) ""
    echo $(timestamp) ""


}

installWireshark()
{
    echo $(timestamp) " ==========================   Section 4 ============================"
    echo $(timestamp) " Check and install wireshark. "
    rpm -q wireshark
    installed=$?

    if [ $installed -eq 0 ];then
        echo $(timestamp) " Wireshark already installed."
    else
        echo $(timestamp) " Wireshark is not installed. Installing it."
        yum -y install wireshark
    fi
    doneMessage
}

getHfnEth0AndSWePkt0SipArray()
{
    # Get region.
    local region=""
    
    # Get region.
    region=$(getRegion)
    if [[ -z "$region" ]];then
        errorAndExit "Failed to get region."
    fi
   
    # Get primary ip assigned on SWE PKT0 interface.
    priIpOnSWePkt0=`aws ec2 describe-network-interfaces --filters "Name=addresses.private-ip-address,Values=$SBC_SECONDARY_IP" --region $region | grep -E "PrivateIpAddress" | tail -1 | awk -F ":" '{print $2}' | awk -F "\"" '{print $2}'`
    if [[ -z "$priIpOnSWePkt0" ]];then
        errorAndExit "Failed to get primary Ip assigned on SBC Pkt0."
    fi

    # Get list of secondary ip assigned on SWe PKT0 interface.
    secIpOnSWePkt0List=`aws ec2 describe-network-interfaces --filters "Name=addresses.private-ip-address,Values=$SBC_SECONDARY_IP" --region $region | grep -E "PrivateIpAddress" | grep -v $priIpOnSWePkt0 | awk -F ":" '{print $2}' | awk -F "\"" '{print $2}'`
    if [[ -z "$secIpOnSWePkt0List" ]];then
        errorAndExit "Failed to get list of secondary ip assigned on SBC PKT0 interface."
    fi

    # Sort list of secondary ip assigned on SWe PKT0 interface.
    tmpSipSWePkt0File="/tmp/sipSWePkt0.txt"
    echo " " > $tmpSipSWePkt0File

    for ip in $secIpOnSWePkt0List;
    do
        echo $ip >> $tmpSipSWePkt0File     
    done
    secIpOnSWePkt0SortList=`sort -n -t . -k1,1 -k2,2 -k 3,3 -k4,4 $tmpSipSWePkt0File`
    echo $(timestamp) "List of secondary IP assigned on SWe Pkt0 in sorted order: $secIpOnSWePkt0SortList"

    secIpOnSWePkt0SortArr=( $secIpOnSWePkt0SortList )
    if [[ -z "$secIpOnSWePkt0SortArr" ]];then
        errorAndExit "Array of Secondary IP on SWe Pkt0 is empty."
    fi

    # Get primary ip assigned on HFN public interface(eth0).
    priIpOnHfnEth0=`ip addr show dev eth0 | grep -v secondary | grep inet | grep -v inet6 | awk '{print $2}' | awk -F"/" '{print $1}'`
    if [[ -z "$priIpOnHfnEth0" ]];then
        errorAndExit "Failed to get primary Ip assigned on HFN eth0 interface."
    fi

    # Get list of secondary ip assigned on HFN public interface(eth0).
    secIpOnHfnEth0List=`aws ec2 describe-network-interfaces --filters "Name=addresses.private-ip-address,Values=$priIpOnHfnEth0" --region $region | grep -E "PrivateIpAddress" | grep -v $priIpOnHfnEth0 | awk -F ":" '{print $2}' | awk -F "\"" '{print $2}'`
    if [[ -z "$secIpOnHfnEth0List" ]];then
        errorAndExit "Failed to get list of secondary ip assigned on HFN eth0 interface."
    fi


    # Sort list of secondary ip assigned on HFN Eth0 interface.
    tmpSipHfnEth0File="/tmp/sipHfnEth0.txt"
    echo " " > $tmpSipHfnEth0File     

    for ip in $secIpOnHfnEth0List;
    do
        echo $ip >> $tmpSipHfnEth0File     
    done
    secIpOnHfnEth0SortList=`sort -n -t . -k1,1 -k2,2 -k 3,3 -k4,4 $tmpSipHfnEth0File`
    echo $(timestamp) "List of secondary IP assigned on HFN eth0 in sorted order: $secIpOnHfnEth0SortList"

    secIpOnHfnEth0SortArr=( $secIpOnHfnEth0SortList )
    if [[ -z "$secIpOnHfnEth0SortArr" ]];then
        errorAndExit "Array of Secondary IP on HFN eth0 is empty."
    fi

    # Get EIP associated on secondary ip of HFN public interface(eth0).
    for ip in $secIpOnHfnEth0SortList;
    do
        eip=`aws ec2 describe-addresses --filters "Name=private-ip-address,Values=$ip" --region $region | grep PublicIp | awk -F ":" '{print $2}' | awk -F "\"" '{print $2}'`
        if [[ -z "$eip" ]];then
            errorAndExit "Failed to get EIP on secondary IP $ip"
        else
            echo $(timestamp) "EIP $eip is associated on secondary IP $ip"
        fi
    done
}

main()
{
    #Do this before we redirect all echo messages to log file
    echo 1 >  /proc/sys/net/ipv4/ip_forward
    
    case $1 in
        "setup") 
            preConfigure
            readConfig
            getHfnEth0AndSWePkt0SipArray
            configureNATRules
            configureMgmtNAT
            showCurrentConfig
            installWireshark
            ;;
        "cleanup")
            preConfigure
            readConfig
            routeCleanUp
            doneMessage
            ;;
        *) 
            usage "Unrecognized switch"
            ;;
    esac
}

[[ $# -ne 1 ]] && usage

main $1
