<%namespace name="k8s" file="kubernetes.mako" />\
<%
    namespace="monitoring"
    ntopCm = k8s.attr.ConfigMap("ntopng",namespace,"/etc/",data={"ntopng.conf":'''
--http-port=3000
--disable-login=1
'''})
    cmd = k8s.attr.Command(cmd="ntopng",args=["--community",
    "-d","/var/lib/ntopng",
    "-i","eno3",
    "-i","eno4",
    "-i","cni0",
    "-r","redis.monitoring.svc.cluster.local:6379",
    "--http-port", "3000",
    "--disable-login","1"])

    ntopng = k8s.attr.Container(
        name = "ntopng",
        image = "vimagick/ntopng:latest",
        ports = [
          { "name":"browser-ui","port":3000,"exposedPort":443}
        ],
        volumes=[{"name":"ntopng-data","mountPoint":"/var/lib/ntopng","size":"10Gi"}],
        env={"CONFIG":"/etc/ntopng.conf"},
        cmd=cmd,
        configmaps=[])
    
    redis = k8s.attr.Container(
        name = "redis",
        image = "redis:alpine",
        ports = [
          { "name":"redis","port":6379}
        ],
        volumes= [{"name":"redis-data","mountPoint":"/data","size":"10Gi"}],
        env={},
        cmd=None,
        configmaps=[])


   
%>\
${k8s.deployment(redis.name,namespace,[redis])}
${k8s.daemonset(ntopng.name,namespace,[ntopng],host_network=True,configmaps=[])}