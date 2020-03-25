<%def name="namespace(name)">\
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${name}
---\
</%def>

<%def name="deployment(name,namespace,label,image,ports,volumes=[],env={})">\
% for vol in volumes:
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
% endfor
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
      - name: ${name}
        image: ${image} 
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
      volumes:
        % for vol in volumes:
        - name: ${vol["name"]}
          persistentVolumeClaim:
            claimName: ${vol["name"]}
        % endfor        
---\
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

<%def name="pvc(v)">\
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${volume_name}
  namespace: ${namespace}
spec:
  storageClassName: local-path
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
---\
</%def>