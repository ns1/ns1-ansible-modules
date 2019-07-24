# ns1-ansible-modules

This role is the home for all NS1 specific modules.  It will serve as a preview for the modules submitted to ansible-core.

# Project Overview

NS1 is an authoritative DNS platform providing data-driven global traffic routing and a fully featured REST API. This module unlocks some of the functionality NS1 can offer for ansible. For more information about what is possible check out [ns1.com](ns1.com) and [api docs](https://ns1.com/api/).

Completed Modules:
 - ns1_zone
 - ns1_record

Still Needed:
 - ns1_facts
 - ns1_data_source
 - ns1_data_feed
 - ns1_monitoring_job

# Installation

1. Install this role from ansible-galaxy. 
   ```ansible-galaxy install ns1.ns1```
2. Install NS1 Python SDK version 0.9.19 or greater. Additional information can be found here [ns1-python](https://github.com/ns1/ns1-python).
   ```pip install ns1-python``` 

## Installing the previous version

The previous version of these modules can be installed from ansible-galaxy via `ansible-galaxy install ns1.ns1,v1.0`

# Testing

This module is tested by using ansible directly. 

```
	git clone https://github.com/ns1/ns1-ansible-modules.git
	cd ns1-ansible-module
	ansible-playbook -i local, tests/<name of module to test>.yaml --extra-vars ns1_token=<your NS1 API key> --extra-vars test_zone=<a zone you have at ns1>
```

You can use any test zone to get started, the only requirement is that it's not yet defined on the NS1 platform. That is, you do not need to make the zone authoritative through your registrar for the ansible module to work correctly.

The current version of the module has been tested with Ansible 2.8.2 and python 3.7.2.

# Examples

Check out the integration tests in `tests/`, which is all working ansible code. All of the resources try to model the [api](https://ns1.com/api/) objects as closely as possible. 

# Contributing

Contributions, ideas and criticisms are all welcome. Please keep the integration tests up to date or add new ones if you do wind up hacking on the project.

# Notes

When creating filters on records you have to use the full syntax required by the REST API to prevent ansible from updating the resources each time. For example the filters field should look like 
```
filters:
  - filter: "up"
    config: {}
```
Not
```
filters:
  - filter: {}
```
Even though it still creates the correct resources. It calls out to the api to update each time.
