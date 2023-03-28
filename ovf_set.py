from subprocess import run, PIPE
from datetime import datetime
from time import sleep
from os import path
from lxml import etree
from config import *

def check_os(osrel_file=OSRELEASE):
    osname = ''
    with open(osrel_file, 'rt') as osrelease_file:
        for line in osrelease_file:
            if line.startswith('NAME'):
                if 'ubuntu' in line.lower():
                    osname = 'ubuntu'
                elif ('centos' in line.lower()) or ('redhat' in line.lower()):
                    osname = 'centos'
                else:
                    # unknown OS
                    osname = line.lstrip('NAME=').replace('"','')
    return osname

def netmask_to_cidr(m_netmask):
    # convert m_netmask to cidr
    return(sum([ bin(int(bits)).count("1") for bits in m_netmask.split(".") ]))

def parse_xml(xml_file):
    # parse xml with VM properties generated with 'vmtoolsd --cmd "info-get guestinfo.ovfenv"' command
    tree = etree.parse(xml_file, parser=etree.XMLParser(remove_comments=True))
    root = tree.getroot()
    vm_properties = {}
    # namespace for VMware OVF Properties
    nsmap = {'oe': 'http://schemas.dmtf.org/ovf/environment/1'}
    # search recursively for Property section
    for property in root.findall('.//oe:Property', nsmap):
        key = property.attrib.values()[0]
        value = property.attrib.values()[1]
        # save property name (key) and value to dictionary
        vm_properties[key] = value
    return(vm_properties)

def generate_netplan(ip_mask, gateway, dns1, dns2, netplan_tpl=NETPLAN_TPL, netplan_cfg=NETPLAN_CFG):
    # generate netplan config (NETPLAN_CFG) based on NETPLAN_TPL template
    with open(netplan_tpl) as netplan_file:
        netplan = netplan_file.read()
        netplan = netplan.replace('IP_MASK', ip_mask)
        netplan = netplan.replace('GATEWAY', gateway)
        netplan = netplan.replace('DNS1', dns1)
        netplan = netplan.replace('DNS2', dns2)
    # open NETPLAN_CFG and write new configuration
    with open(netplan_cfg, 'w+') as netplan_cfg_file:
        netplan_cfg_file.write(netplan)
    # save new netplan in /etc/netplan and apply new settings
    run(f'mv {netplan_cfg} /etc/netplan/', shell=True)
    run('netplan apply', shell=True)

def generate_network_scripts(ip, netmask, gateway, dns1, dns2, ifcfg_tpl=IFCFG_TPL, ifcfg=IFCFG):
    # generate network script (IFCFG) for ens192 NIC based on IFCFG_TPL template
    with open(ifcfg_tpl) as ifcfgtpl_file:
        ifcfgtpl = ifcfgtpl_file.read()
        ifcfgtpl = ifcfgtpl.replace('VMIPADDR', ip)
        ifcfgtpl = ifcfgtpl.replace('VMNETMASK', netmask)
        ifcfgtpl = ifcfgtpl.replace('VMGW', gateway)
        ifcfgtpl = ifcfgtpl.replace('VMDNS1', dns1)
        ifcfgtpl = ifcfgtpl.replace('VMDNS2', dns2)
    # save customized ifcfg script as 'ifcfg'
    with open(ifcfg, 'w+') as ifcfg_file:
        ifcfg_file.write(ifcfgtpl)
    # restart NetworkManager to load new configuration
    run('systemctl restart NetworkManager', shell=True)


def set_motd_warning(noip_warn_file=NOIP_WARN):
    print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Setting MOTD warning: {noip_warn_file}')
    run(f'cp {noip_warn_file} /etc/update-motd.d/', shell=True)


def remove_motd_warning(noip_warn_file=NOIP_WARN):
    motd_warn = path.join('/etc/update-motd.d/', path.basename(noip_warn_file))
    if path.isfile(motd_warn):
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Removing MOTD warning: {motd_warn}')
        run(f'rm -f {motd_warn}', shell=True)


def setup_network(state, tmpxml, osname, banner=BANNER):
    if path.isfile(state):
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] {state} file exists. Doing nothing.')
        exit()
    else:
        print(banner)
        
        # create XML file with settings
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Fetching values from vmtools...')
        run(f'vmtoolsd --cmd "info-get guestinfo.ovfenv" > {tmpxml}', shell=True)
        if not path.isfile(tmpxml):
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] {tmpxml} file does not exist!')
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] Check if vmtoolsd --cmd "info-get guestinfo.ovfenv" command works correcty.')
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] Aborting.')
            exit()

        # get network settings from TMPXML file
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Parsing xml...')
        # parse xml output to dictionary
        vm_settings = parse_xml(tmpxml)
        ip = vm_settings.get('IP')
        netmask = vm_settings.get('Netmask')
        if netmask:
            netmask_cidr = netmask_to_cidr(netmask)
            ip_mask = ip + '/' + str(netmask_cidr)
        gateway = vm_settings.get('Gateway')
        dns1 = vm_settings.get('DNS1')
        dns2 = vm_settings.get('DNS2')
        if not dns1 and not dns2:
            dns = ''
        elif dns1 and not dns2:
            dns = dns1
        elif not dns1 and dns2:
            dns = dns2
        else:
            dns = f'{dns1}, {dns2}'
        print('\n### VM OVF vApp settings ###')
        print(f'IP address: {ip}')
        print(f'Netmask: {netmask}')
        print(f'Gateway address: {gateway}')
        print(f'DNS: {dns}\n')

        # check if netmask, IP and Gateway addresses have been provided - set MOTD warning and stop execution here
        if not ip or not netmask or not gateway:
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] Netmask, IP or Gateway address missing - cannot set VM IP address!')
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] Please review VM vApp Options or modify /etc/netplan/01-netcfg.yaml manually and restart the system.\n')
            set_motd_warning()
            exit()

        if osname in 'ubuntu':
            # on Ubuntu - setup network using netplan
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Discovered Ubuntu Linux - generating netplan configuration...')
            generate_netplan(ip_mask, gateway, dns1, dns2)
        elif osname in 'centos':
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Discovered CentOS/RedHat - generating network scripts...')
            # on CentOS - setup network using /etc/sysconfig/network-scripts
            generate_network_scripts(ip, netmask, gateway, dns1, dns2)
        else:
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] Unknown OS version: {osname}')
            exit()

        # check if IP address has been set
        check = run(f'ip a | grep -c {ip}', shell=True, stdout=PIPE, text=True)
        if int(check.stdout) < 1:
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] VM IP address not set!')
            print(f'{datetime.now().strftime("%Y-%m-%d %X")} [ERROR] Please review VM vApp Options or modify /etc/netplan/01-netcfg.yaml manually and restart the system.\n')
            set_motd_warning()
            exit()
        
        # Notification for future in case IP address has been set successfully
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] IMPORTANT: This script will not be executed on next boot if {state} file exists')
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] IMPORTANT: If you want to execute this configuration on Next boot remove {state} file')

        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Creating State file')
        with open(state, 'w+') as state_file:
            state_file.write(datetime.now().strftime("%Y-%m-%d %X"))
            
        # check if MOTD exisis and remove/update
        remove_motd_warning()

        # Wait a bit and reboot
        sleep(5)
        print(f'{datetime.now().strftime("%Y-%m-%d %X")} [INFO] Rebooting the system...\n')
        run('reboot')

if __name__ == "__main__":
    setup_network(STATE, TMPXML, check_os())
