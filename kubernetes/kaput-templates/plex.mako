<%namespace name="k8s" file="kubernetes.mako" />\
<% 
    name = "plex"
    namespace = "filesharing"
    plex = k8s.attr.Container(
        name = name,
        image = "linuxserver/plex:latest",
        ports = [
            { "name":"http","port":32400,"exposedPort":80},
            { "name":"plex-ht-control","port":3005},
            { "name":"dlna-tcp","port":32469},
            { "name":"dlna-udp","port":1900,"protocol":"UDP"},
            { "name":"avahi","port":5353,"protocol":"UDP"},
            { "name":"gdm1","port":32410,"protocol":"UDP"},
            { "name":"gdm2","port":32412,"protocol":"UDP"},
            { "name":"gdm3","port":32413,"protocol":"UDP"},
            { "name":"gdm4","port":32414,"protocol":"UDP"},              
        ],
        volumes = [
            {"name":"host-media","mountPoint":"/media","hostPath":"/media/media"},
            {"name":name+"-config","mountPoint":"/config","size":"10Gi"}
        ],
         env={
            "PUID":"1000",
            "PGID":"1000",
            "TZ":"America/New_York",
            "NVIDIA_VISIBLE_DEVICES":"all",
            "PLEX_CLAIM":"claim-ArCWwreSxsnNVHhhVBsV"            
        },
        cmd=[],
        configmaps=[])
%>\
${k8s.deployment(plex.name,namespace,[plex])}\