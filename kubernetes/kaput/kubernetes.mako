<%!
    from collections import namedtuple
    ConfigMap = namedtuple("ConfigMap",["name","namespace", "mountPath", "data"])    
    Command = namedtuple("Command",["cmd","args"])
    Container = namedtuple("Container",["name","image","cmd","env","ports","volumes","configmaps"])
%>

<%def name="namespace(name)">\
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${name}
---\
</%def>

<%def name="deployment(name,namespace,containers,configmaps=[])">\
<% 
  def all_volumes(containers):
    volumes = []
    for c in containers:
      for v in c.volumes:
        volumes.append(v)
    return volumes
  label = name
  volumes = all_volumes(containers)
%>
% for vol in volumes:
%if "hostPath" not in vol:
${pvc(vol,namespace)}
%endif
% endfor
%for cm in configmaps:
${configmap(cm)}
%endfor
%for c in containers:
${service(name,namespace,name,c.ports)}
%endfor
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${name}
  namespace: ${namespace}
  labels:
    app: ${label}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${label}
  template:
    metadata:
      labels:
        app: ${label}
    spec:
      containers:
    % for cspec in containers:
    ${container(cspec)}\
    % endfor
      volumes:
        % for vol in volumes:
        ${volume(vol)}
        % endfor 
---\
</%def>

<%def name="volume(vol)">\
- name: ${vol["name"]}
% if "hostPath" in vol:
          hostPath:
            path: ${vol["hostPath"]}
            type: Directory
% else:
          persistentVolumeClaim:
            claimName: ${vol["name"]}
% endif

</%def>

<%def name="service(name,namespace,label,ports)">\
---
apiVersion: v1
kind: Service
metadata:
  name: ${name}
  namespace: ${namespace}
spec:
  selector:
    app: ${label}
  ports:
  % for port in ports:
  - name: ${port["name"]}
    port: ${port.get("exposedPort",port["port"])}
    targetPort: ${port["port"]}
    protocol: ${port.get("protocol","TCP")}
  % endfor
---\
</%def>

<%def name="container(container)">\
  <%
    command = container.cmd
    env = container.env
    ports = container.ports
    volumes = container.volumes
    configmaps = container.configmaps
  %>\
- name: ${container.name}
        image: ${container.image} 
        % if command:
        command: ["${command.cmd}"]
        args:
        % for arg in command.args:
        - "${arg}"
        %endfor
        % endif
        % if env:
        env:
        % for key, val in env.items():
        - name: ${key}
          value: "${val}"
        % endfor
        % endif
        % if ports:
        ports:
        % for port in ports:
        - name: ${port["name"]}
          containerPort: ${port["port"]}
          protocol: ${port.get("protocol","TCP")}
        % endfor   
        % endif     
        volumeMounts:
        % for vol in volumes:
        - name: ${vol["name"]}
          mountPath: ${vol["mountPoint"]}
        % endfor
        % for cm in configmaps:
        %  for key in cm.data.keys():
        - name: ${cm.name}
          mountPath: ${cm.mountPath}${key}
          subPath: ${key}
        %  endfor
        % endfor         
</%def>

<%def name="daemonset(name,namespace,containers,configmaps=[],host_network=False)">\
<% 
  def all_volumes(containers):
    volumes = []
    for c in containers:
      for v in c.volumes:
        volumes.append(v)
    return volumes
  label = name
  volumes = all_volumes(containers)
%>
% for vol in volumes:
${pvc(vol,namespace)}
% endfor
%for cm in configmaps:
${configmap(cm)}
%endfor
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ${name}
  namespace: ${namespace}
  labels:
    app: ${label}
spec:
  selector:
    matchLabels:
      app: ${label}
  template:
    metadata:
      labels:
        app: ${label}
    spec:
      hostNetwork: ${host_network}
      containers:
    % for cspec in containers:
    ${container(cspec)}\
    % endfor
      volumes:
    % for vol in volumes:
    ${volume(vol)}
    % endfor 
      % for cm in configmaps:
      - name: ${cm.name}
        configMap:
          name: ${cm.name}            
    % endfor       
---\
</%def>

<%def name="configmap(cm)">\
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${cm.name}
  namespace: ${cm.namespace}
data:
  % for key,val in cm.data.items():
    "${key}": "${val}"
  %endfor
---
</%def>

<%def name="pvc(vol,namespace)">\
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${vol["name"]}
  namespace: ${namespace}
spec:
  storageClassName: local-path
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: ${vol["size"]}
---
</%def>