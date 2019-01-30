This Ansible Playbook is to provide a golden config for below deployment.


Softphone(UAC) ------- (pkt0-untrusted)--AWS SBC--(pkt1-trusted)------Asterisk
Softphone(UAS) -------


The routing is Number Based routing , calling number should be 98402. If call comes in on  Ingress TG it will be sent to Egress TG and anything that comes on Egress TG will be sent to Ingress TG

Note: Based on our requirement , we can customise the routing methods.
Explanation:
Registers coming in on Ingress TG will be sent to Egress TG (ippeer will be asterisk) and the asterisk will have the EPs registered

UAC Invite on Ingress TG will be sent to Egress TG (ippeer will be asterisk) and asterisk will send Invite back to Egress TG on SBC with dtg info which will then be sent to Ingress TG and then to UAS

