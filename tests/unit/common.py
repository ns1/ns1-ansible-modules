from ansible.module_utils._text import to_bytes
from ansible.module_utils import basic
import json

try:  # Python 3.3 +
    from unittest.mock import ANY
except ImportError:
    from mock import ANY


class FakeAnsibleModule:
    def __init__(self, name):
        self.name = name

    @staticmethod
    def set_module_args(args):
        """prepare arguments so that they will be picked up during module creation"""
        args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
        basic._ANSIBLE_ARGS = to_bytes(args)

    @staticmethod
    def exit_json(*args, **kwargs):
        """function to patch over exit_json; package return data into an exception"""
        if 'changed' not in kwargs:
            kwargs['changed'] = False
        raise AnsibleExitJson(kwargs)

    @staticmethod
    def fail_json(*args, **kwargs):
        """function to patch over fail_json; package return data into an exception"""
        kwargs['failed'] = True
        raise AnsibleFailJson(kwargs)

    def get_bin_path(self, arg, required=False):
        """Mock AnsibleModule.get_bin_path"""
        if arg.endswith('my_command'):
            return '/usr/bin/my_command'
        else:
            if required:
                self.fail_json(msg='%r not found !' % arg)

    def get_zone_data(self, **kwargs):
        data = {"zone": self.name}
        data.update(**kwargs)
        return data

    def get_args(self, **kwargs):
        args = {"name": self.name, "apiKey": "testkey"}
        args.update(**kwargs)
        return args

    def get_request_args(self, **kwargs):
        args = {"errback": ANY}
        args.update(**kwargs)
        return args


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass
