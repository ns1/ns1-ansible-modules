# -*- coding: utf-8 -*-

# Copyright: (c) 2019, Matthew Burtless <mburtless@ns1.com>
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible.module_utils.basic import missing_required_lib
except ImportError:
    def missing_required_lib(msg, reason=None, url=None):
        return msg

HAS_NS1 = True

try:
    from ns1 import NS1, Config
    from ns1.rest.errors import ResourceException
except ImportError:
    HAS_NS1 = False


NS1_COMMON_ARGS = dict(
    apiKey=dict(required=True, no_log=True),
    endpoint=dict(required=False, type='str', default=None),
    ignore_ssl=dict(required=False, type='bool', default=None)
)


class NS1ModuleBase(object):
    def __init__(self, derived_arg_spec, supports_check_mode=False,
                 mutually_exclusive=None):
        merged_arg_spec = dict()
        merged_arg_spec.update(NS1_COMMON_ARGS)
        if derived_arg_spec:
            merged_arg_spec.update(derived_arg_spec)

        self.module = AnsibleModule(
            argument_spec=merged_arg_spec,
            supports_check_mode=supports_check_mode,
            mutually_exclusive=mutually_exclusive
        )

        if not HAS_NS1:
            self.module.fail_json(msg=missing_required_lib("ns1-python"))
        self._build_ns1()

    def _build_ns1(self):
        self.config = Config()
        self.config.createFromAPIKey(self.module.params["apiKey"])
        self.config['transport'] = 'basic'
        if self.module.params["endpoint"]:
            self.config["endpoint"] = self.module.params["endpoint"]
        if self.module.params["ignore_ssl"]:
            self.config["ignore-ssl-errors"] = self.module.params["ignore_ssl"]
        self.ns1 = NS1(config=self.config)

    def errback_generator(self):
        def errback(args):
            self.module.fail_json(msg="%s - %s" % (args[0], args[1]))

        return errback
