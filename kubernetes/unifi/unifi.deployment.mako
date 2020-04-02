<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "unifi-controller"
    namespace="unifi"
    unifi = k8s.attr.Container(
        name = name,
        image = "linuxserver/unifi-controller:latest",
        ports = [
            { "name":"unifi-comms","port":8080},
            { "name":"browser-ui","port":8443,"exposedPort":443},
            { "name":"http-redir","port":8880},
            { "name":"https-redir","port":8843},
            { "name":"speed-test","port":6789},
            { "name":"dev-discovery","port":10001,"protocol":"UDP"},
            { "name":"l2-discovery","port":1900,"protocol":"UDP"},
            { "name":"stun","port":3478,"protocol":"UDP"},
        ],
        volumes=[{"name":name+"-data","mountPoint":"/config","size":"2Gi"}],
        env={
            "PUID":"1000",
            "PGID":"1000"
        },
        cmd=[],
        configmaps=[])
%>

${k8s.namespace(namespace)}
${k8s.deployment(unifi.name,namespace,[unifi])}
