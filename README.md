# ovfset
ovfset is a simple Python script allowing to set VMware Virtual Machine network settings using VM vApp Options properties passed through vmtoolsd. On VM side it is launched via /etc/rc.local. Successful run creates lock file (default: /opt/ovfset/state) so that the script isn't run on the next reboot.

Note: if you want to use the script in OVF template remember to remoce `state` lock file before exporting OVF template.

## pre-requisites
- enabled and set vApp Options with the following Properties
  - IP
  - Gateway
  - Netmask
  - DNS1
  - DNS2
- installed Python and lxml library
- installed and running VMware tools
- rc.local script (see example below)

### Enable Virtual Machine vApp Operations
Please refer to VMware documentation for enabling and setting vApp Options, eg. https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.vm_admin.doc/GUID-A6F34BAC-BF8B-4513-AB8C-14891B439D2D.html

### Install Python and lxml library
Below example applies to Ubuntu and all Linux distros using apt package management system:
```
apt update
apt install python3-pip
pip3 install lxml
```

### VMware tools
Install VMware Tools:
```
apt update
apt install open-vm-tools
```

Once VM tools are running you should be able to run the following command, which is in fact used by `ovf_set.py` script to extract vApp Options:
```
$ vmtoolsd --cmd "info-get guestinfo.ovfenv"
<?xml version="1.0" encoding="UTF-8"?>
<Environment
     xmlns="http://schemas.dmtf.org/ovf/environment/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xmlns:oe="http://schemas.dmtf.org/ovf/environment/1"
     xmlns:ve="http://www.vmware.com/schema/ovfenv"
     oe:id=""
     ve:vCenterId="vm-41857">
   <PlatformSection>
      <Kind>VMware ESXi</Kind>
      <Version>6.7.0</Version>
      <Vendor>VMware, Inc.</Vendor>
      <Locale>en</Locale>
   </PlatformSection>
   <PropertySection>
         <Property oe:key="DNS1" oe:value="8.8.8.8"/>
         <Property oe:key="DNS2" oe:value="8.8.4.4"/>
         <Property oe:key="Gateway" oe:value="10.10.10.1"/>
         <Property oe:key="IP" oe:value="10.10.10.100"/>
         <Property oe:key="Netmask" oe:value="255.255.255.0"/>
   </PropertySection>
   <ve:EthernetAdapterSection>
      <ve:Adapter ve:mac="00:50:56:ad:0b:2c" ve:network="MGT" ve:unitNumber="7"/>
   </ve:EthernetAdapterSection>
</Environment>
```

`ovf_set.py` script parses network details from `<PropertySection>` and uses `NETPLAN_TPL` (Ubuntu) or `IFCFG_TPL` (CentOS/RedHat) templates to set network settings.

### /etc/rc.local script example
The script has to be run on first VM boot up. rc.local script should be considered as rather 'legacy approach', given that modern Linux systems use systemd, however it's left here as an example implementation that works. Most important part is `start` case where `ovf_set.py` script is launched and it's output is redirected to `run.log`

```
root@ucs-auto-tuner:~# cat /etc/rc.local
#!/bin/bash
# THIS FILE IS ADDED FOR COMPATIBILITY PURPOSES
#
# It is highly advisable to create own systemd services or udev rules
# to run scripts during boot instead of using this file.
#
# In contrast to previous versions due to parallel execution during boot
# this script will NOT be run after all other services.
#
# Please note that you must run 'chmod +x /etc/rc.d/rc.local' to ensure
# that this script will be executed during boot.

touch /var/lock/subsys/local

set -e

case "$1" in
  start)
  	/usr/bin/python3 -u /opt/ovfset/ovf_set.py 2>&1 | tee -a /opt/ovfset/run.log
  	;;

  stop)
  	echo "Stop not implemented"
  	;;

  status)
  	echo "Checking for lock file:"
  	ls -l /opt/ovfset/state
  	;;
esac

exit 0
```

### Clone git repo
Note: default location is `/opt` however if you need to change this rememebr to update file paths
```
cd /opt
git clone https://github.com/mikeslowik/ovfset.git
```

## Troubleshooting
- check if `state` lock file exists - if it doesn't then the script didn't run successfully
- check `run.log` for details
- run the script manually; normal script run should render output similar to the one below:
```
root@server1 # python3 /opt/ovfset/ovf_set.py

*******************************************
*            OVF Config script            *
* System will be rebooted after execution *
*******************************************

2021-08-25 15:24:59 [INFO] Fetching values from vmtools...
2021-08-25 15:24:59 [INFO] Parsing xml...
### VM settings ###
IP: 10.10.10.100
Netmask: 255.255.255.0
IP_MASK: 10.10.10.100/24
GW: 10.10.10.1
DNS: 8.8.8.8, 8.8.4.4

2021-08-25 15:24:59 [INFO] Discovered CentOS/RedHat - generating network scripts...
2021-08-25 15:24:59 [INFO] IMPORTANT: This script will not be executed on next boot if /opt/ovfset/state file exists
2021-08-25 15:24:59 [INFO] IMPORTANT: If you want to execute this configuration on Next boot remove /opt/ovfset/state file
2021-08-25 15:24:59 [INFO] Creating State file
2021-08-25 15:25:04 [INFO] Rebooting the system...
```