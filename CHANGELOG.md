## 3.1.2 (October 10, 2024)
BUGFIX:
* Fix deprecated use of raumel.yaml

## 3.1.1 (September 7, 2023)
ENHANCEMENTS:
* Adds support for CAA record type

## 3.1.0 (March 30, 2022)
ENHANCEMENTS:
* Adds support for TSIG

## 3.0.1 (January 04, 2021)

ENHANCEMENTS
* Add region support to answer parameters (thanks @tsimson!)

## 3.0.0 (February 24, 2020)

BREAKING CHANGES
* ns1_zone: Adds fully defined suboptions for `secondary` and `primary` options. These previously accepted arbitrary dict as values.
* ns1_zone: Returned zone data is now returned in a key named `zone` (was previously returned in `data`).

FEATURES
* Adds ns1_datasource_info module for read-only listing of available datasources and their feeds

ENHANCEMENTS
* ns1_record: Supresses answer level feeds list from diff comparison. This is maintained API-side based on the connected feed(s), it shouldn't trigger a change event.
* ns1_zone: Refactor for readability and linting.
* Adds unit tests

## 2.1.0 (January 13, 2020)

ENHANCEMENTS
* Add support to both modules for setting custom API endpoint and ignoring SSL verification ([#23](https://github.com/ns1/ns1-ansible-modules/pull/23))

## 2.0.0 (August 05, 2019)

ENHANCEMENTS
* ns1_zone: Adds `dnssec` option
* ns1_record: Adds `record_mode` option to allow appending new answers or filters to existing values unspecified in the playbook or purging of unspecified values

IMPROVEMENTS
* Fixes support for Falsey option values
* Role now associated with dedicated `ns1` namespace in Ansible Galaxy
