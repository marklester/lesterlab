#!/bin/bash
set -e
echo -n "Govee Email:" 
read email
# Read Password
echo -n "Govee Password:" 
read -s password

echo -n "Govee API Key:" 
read -s apikey
echo 
kubectl create secret generic govee-credentials -n mqtt --from-literal=email="${email}" \
 --from-literal=password="${password}" \
 --from-literal=api-key="${apikey}"