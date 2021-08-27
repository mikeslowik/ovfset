# ovfset config
from os import path

WORKDIR = '/opt/ovfset'
TMPDIR = '/tmp'
STATE = path.join(WORKDIR, 'state')
# customize NIC name to your system in NETPLAN_TPL or IFCFG_TPL template file
NETPLAN_TPL = path.join(WORKDIR, 'netplan-config.tpl')
NETPLAN_CFG = path.join(TMPDIR, '01-netcfg.yaml')
IFCFG_TPL = path.join(WORKDIR, 'ifcfg-ens192')
IFCFG = '/etc/sysconfig/network-scripts/ifcfg-ens192'

TMPXML = path.join(TMPDIR, 'ovf_env.xml')
OSRELEASE = '/etc/os-release'
banner = """
*******************************************
*            OVF Config script            *
* System will be rebooted after execution *
*******************************************
"""