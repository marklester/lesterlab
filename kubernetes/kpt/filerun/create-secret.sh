#!/bin/bash
echo -n "root_pass:" 
read -s root_pass
# Read Password
echo -n "app_pass:" 
read -s app_pass
echo 
kubectl create secret generic db-credentials -n filerun --from-literal=root_pass="${root_pass}" --from-literal=app_pass="${app_pass}"