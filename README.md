nsone-ansible-module
====================

This is the temporary home for the nsone-ansible modules. Once additional resources are completed and reviewed we will look to have these merged into the community core modules so they can be distributed with mainline ansible.

Project Overview
================

Nsone is a first class anycast DNS provider with a highly mutable api. This module unlocks some of the functionality NSONE can offer for ansible. For more information about what is possible check out [nsone.com](nsone.com) and [api docs](https://nsone.net/api/).

Completed Modules:
 - nsone_zone
 - nsone_record

Still Needed:
 - nsone_facts
 - nsone_data_source
 - nsone_data_feed
 - nsone_monitoring_job

Installation
============

For now the easiest way to install these modules is to copy them into your ansible library directory. You will need the nsone python client version 0.9.2 or greater. This can be installed by running: `pip install nsone`. Additional information can be found here [nsone-python](https://github.com/nsone/nsone-python)

Testing
=======

This module is tested by using ansible directly. 

	git clone git@github.com/nsone/nsone-ansible-module.git
	cd nsone-ansible-module
	ansible -i local, test.yml --extra-vars key=<your nsone api key> --extra-vars debug=yes --extra-vars test_zone=<a zone you have at nsone

The debug flag is optional. As far as setting up a test zone you don't need to own a domain to get started. You just need to pick a domain isn't already in use by an existing nsone customer. So any random string.com would work for testing.

This was tested with ansible 1.9.2 and python 2.7.10.

Examples
========

Check out test.yml which is all working ansible code. We will be adding the standard ansible documentation to the modules themselves shortly.

Contributing
============

Contributions, ideas and criticisms are all welcome. Please keep the anisble test.yml up to date if you do wind up hacking on this project.

Notes:
=====
 When creating filters on records you have to use the full syntax to prevent ansible from updating the resources each time. For example the filters field should look like 

	filters:
	  - filter: "up"
	    config: {}

 Not

 	filters:
 	  - filter: {}

 Even though it still creates the correct resources. It calls out to the api to update each time.
