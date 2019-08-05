## 2.1.0 (Unreleased)

## 2.0.0 (August 05, 2019)

BREAKING CHANGES
* ns1_zone: `next_ttl` option renamed `nx_ttl`

ENHANCEMENTS
* ns1_zone: Adds `dnssec` option
* ns1_record: Adds `record_mode` option to allow appending new answers or filters to existing values unspecified in the playbook or purging of unspecified values

IMPROVEMENTS
* Fixes support for Falsey option values
* Role now associated with dedicated `ns1` namespace in Ansible Galaxy
