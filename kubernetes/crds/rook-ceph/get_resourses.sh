 
set -ex
VERSION="1.17.8"
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/common.yaml -o common.yaml
curl https://raw.githubusercontent.com/rook/rook/v$VERSION/deploy/examples/crds.yaml -o crds.yaml
