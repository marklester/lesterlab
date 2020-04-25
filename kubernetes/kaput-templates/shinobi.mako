<%namespace name="k8s" file="kubernetes.mako" />
<% 
    name = "shinobi"
    namespace = "cams"
    shinobi = k8s.attr.Container(
        name = name,
        image = "registry.gitlab.com/migoller/shinobidocker:nvidia",
        ports = [
            { "name":"http","port":8080,"exposedPort":80},
        ],
        volumes = [
            {"name":"videos","mountPoint":"/opt/shinobi/videos","hostPath":"/media/media/cctv"},
            {"name":name+"-mysql-data","mountPoint":"/var/lib/mysql","size":"10Gi"},
            {"name":name+"-shm","mountPoint":"/dev/shm/","emptyDir":True},
        ],
         env={
             "APP_BRANCH":"dev",
            ##  "NVIDIA_DRIVER_CAPABILITIES":"compute,video,utility",
            ##  "NVIDIA_VISIBLE_DEVICES":"all",
        },
        cmd=[],
        configmaps=[])
%>
${k8s.namespace(namespace)}

${k8s.deployment(shinobi.name,namespace,[shinobi])}
