<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "unifi-controller"
    namespace="unifi"
    volumes = [{"name":name+"-data","mountPoint":"/config","size":"2Gi"}]
    image = "linuxserver/unifi-controller:latest" 
    label = name 
    ports = [
        { "name":"unifi-comms","port":8080},
        { "name":"browser-ui","port":8443,"exposedPort":443},
        { "name":"http-redir","port":8880},
        { "name":"https-redir","port":8843},
        { "name":"speed-test","port":6789},
        { "name":"dev-discovery","port":10001,"protocol":"UDP"},
        { "name":"l2-discovery","port":1900,"protocol":"UDP"},
        { "name":"stun","port":3478,"protocol":"UDP"},
    ]
    env = {
        "PUID":"1000",
        "PGID":"1000"
    }
%>

${k8s.namespace(namespace)}
${k8s.deployment(name,namespace,label,image=image,ports=ports,volumes=volumes,env=env)}
${k8s.service(name,namespace,label,ports=ports)}
