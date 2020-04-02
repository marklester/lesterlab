<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "unms"
    namespace="unifi"
    unms = k8s.attr.Container(
        name = name,
        image = "nico640/docker-unms",
        ports = [
            { "name":"unifi-comms","port":80},
            { "name":"browser-ui","port":443},
            { "name":"netflow","port":2055,"protocol":"UDP"},
        ],
        volumes=[{"name":name+"-data","mountPoint":"/config","size":"2Gi"}],
        env={"TZ":"America/New_York"},
        cmd=[],
        configmaps=[])
%>

${k8s.deployment(name,namespace,[unms])}
