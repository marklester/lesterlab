# How to Export syslog to Influxdb on PFSense

With PFSense 2.4.5-RELEASE-p1 telegraf can't understand the output of the data sent via the built in syslog. To get around this I install syslog-ng and pull from the builtin and send it to telegraf in tcp mode.

## Install telegraf
### configure telegraf
* Go to Services->Telegraf
    ```
    Enable: Yes
    Telegraf Output: InfluxDB
    InfluxDB Server: <influxdbIp>:<Port> 
    Additional configuration for Telegraf: 
    [[inputs.syslog]]
    server = "tcp://:6514
    ```
## Install syslog-ng

### Configure syslog-ng

Go to Services->Syslog-ng
* General Options
    ```
    Enable: Yes
    Interface Selection: loopback
    Default Protocol: UDP
    ```
#### Add Advanced Settings

* Services->Syslog-ng->Advanced
* Add Destination
    ```
    General Options
    Object Name: telegraf
    Object Type: Destination
    Object Parameters:
    {syslog("127.0.0.1" port(6514));};
    Description: output to telegraf
    ```
* Add Log
    ```
    General Options
    Object Name: log_to_telegraf
    Object Type: Log
    Object Parameters:
    { source(_DEFAULT); destination(telegraf); };
    Description: log to telegraf
    ```

## configure syslog
1. go to Status->System Logs->Settings
    ```
    Enable Remote Logging: Yes
    Remote log servers: 127.0.0.1:5140
    Remote Syslog Contents: Everything
    ```