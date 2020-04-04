<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "samba"
    namespace = "filesharing"
    samba = k8s.attr.Container(
        name = name,
        image = "dperson/samba:latest",
        ports = [
            { "name":"netbios-session","port":139},
            { "name":"smb","port":445},
            { "name":"nb-name-service","port":137,"protocol":"UDP"},
            { "name":"nb-datagram","port":138,"protocol":"UDP"}
        ],
        volumes = [{"name":name+"-share","mountPoint":"/shares","hostPath":"/media"}],
        env={
            "SHARE":"gimli-share;/shares/;yes;no;yes;",
            "NMDB":"true",
            "WORKGROUP":"WORKGROUP"
        },
        cmd=[],
        configmaps=[])
%>

${k8s.namespace(namespace)}
${k8s.deployment(samba.name,namespace,[samba])}
