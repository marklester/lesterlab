#!/bin/bash
echo -n "username:" 
read username
# Read Password
echo -n "password:" 
read -s password
echo 
kubectl create secret generic vpn-credentials -n transmission --from-literal=username="${username}" --from-literal=password="${password}"