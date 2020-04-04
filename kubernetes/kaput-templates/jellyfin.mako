<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "jellyfin"
    namespace = "filesharing"
    jellyfin = k8s.attr.Container(
        name = name,
        image = "linuxserver/jellyfin:latest",
        ports = [
            { "name":"http","port":8096,"exposedPort":80},
            { "name":"https","port":8920,"exposedPort":443}
        ],
        volumes = [
            {"name":"host-media","mountPoint":"/data","hostPath":"/media/media"},
            {"name":name+"-config","mountPoint":"/config","size":"10Gi"}
        ],
         env={
            "PUID":"1000",
            "PGID":"1000",
            "TZ":"America/New_York",
            "NVIDIA_VISIBLE_DEVICES":"all"
        },
        cmd=[],
        configmaps=[])
%>

${k8s.deployment(jellyfin.name,namespace,[jellyfin])}
