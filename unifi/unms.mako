<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "unms"
    namespace="unifi"
    volumes = [{"name":name+"-data","mountPoint":"/config","size":"2Gi"}]
    image = "nico640/docker-unms" 
    label = name 
    ports = [
        { "name":"unifi-comms","port":80},
        { "name":"browser-ui","port":443},
        { "name":"netflow","port":2055,"protocol":"UDP"},
    ]
    env = {
        "TZ":"America/New_York"
    }
%>

${k8s.deployment(name,namespace,label,image=image,ports=ports,volumes=volumes,env=env)}
${k8s.service(name,namespace,label,ports)}