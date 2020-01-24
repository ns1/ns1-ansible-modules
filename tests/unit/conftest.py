import pytest
from ns1 import Config
from ansible.module_utils import basic
from .common import FakeAnsibleModule

try:  # Python 3.3 +
    from unittest.mock import patch
except ImportError:
    from mock import patch


@pytest.fixture
def zones_update_helper(request):
    zones_update_helper = patch("ns1.zones.Zone.update")
    zones_update_helper.start()
    request.addfinalizer(zones_update_helper.stop)


@pytest.fixture
def ns1_config():
    c = Config()
    c.loadFromDict(
        {
            "endpoint": "api.nsone.net",
            "default_key": "test1",
            "keys": {
                "test1": {
                    "key": "key-1",
                    "desc": "test key number 1",
                    "writeLock": True,
                }
            },
        }
    )
    return c


@pytest.fixture()
def mock_module_helper(request):
    mock_module_helper = patch.multiple(
        basic.AnsibleModule,
        exit_json=FakeAnsibleModule.exit_json,
        fail_json=FakeAnsibleModule.fail_json,
        get_bin_path=FakeAnsibleModule.get_bin_path,
    )
    mock_module_helper.start()
    request.addfinalizer(mock_module_helper.stop)
