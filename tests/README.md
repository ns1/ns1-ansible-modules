# Testing
Tests in this directory can be run via ansible directly:
```
ansible-playbook -i local, ns1_record.yml --extra-vars ns1_token=$NS1_APIKEY --extra-vars debug=yes -M ../library
```
