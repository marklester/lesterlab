## 5. setup DNS and DHCP
Dnsmasq can function both as dns and dhcp. It also works well for local dns. Configuration is also pretty straight forward
* install dnsmasq
  * configure dhcp and dns
`apt install dnsmasq`
  * configure dnsmasq: see [/etc/dnsmasq.d/dnsmasq.conf](network/dnsmasq.conf)

* turnoff systemd-resolved: `systemctl disable systemd-resolved`
* make sure it starts after network is on

    `systemctl edit dnsmasq`

    add:

    ```
    After=network-online.target
    Wants=network-online.target
    ```

* `systemctl enable dnsmasq`

## install firewall
* enable ip forward
in /etc/sysctl.conf uncomment

`net.ipv4.ip_forward=1`

* disable and remove ufw

`systemctl disable ufw`

`apt purge ufw`

`apt install firehol`
set firehol to start in /etc/defaults/firehol.conf

`START_FIREHOL=YES`

setup : [/etc/firehole/firehol.conf](../network/firehol.conf)
TODO 
1. port-forwarding:
    http://manpages.ubuntu.com/manpages/bionic/man5/firehol-nat.5.html
    examples:
    ```
    # Port forwarding HTTP
    dnat4 to 192.0.2.2 proto tcp dport 80

    # Port forwarding HTTPS on to a different port internally
    dnat4 to 192.0.2.2:4443 proto tcp dport 443
    ```
1. narrow accept traffic to valid ip ranges
https://firehol.org/guides/firehol-welcome/