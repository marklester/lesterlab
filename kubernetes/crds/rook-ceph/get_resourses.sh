 
set -ex
VERSION="1.19.11"
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/common.yaml -o common.yaml
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/crds.yaml -o crds.yaml
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/csi-operator.yaml -o csi-operator.yaml
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/monitoring/rbac.yaml -o rbac.yaml
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/toolbox.yaml -o toolbox.yaml
