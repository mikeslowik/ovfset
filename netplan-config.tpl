# This file describes the network interfaces available on your system
# For more information, see netplan(5).
network:
  version: 2
  renderer: networkd
  ethernets:
    ens160:
      addresses: [ IP_MASK ]
      gateway4: GATEWAY
      nameservers:
          addresses:
              - DNS1
              - DNS2
