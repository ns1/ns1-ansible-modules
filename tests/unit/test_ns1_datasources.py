import pytest

from collections import namedtuple

from .common import FakeAnsibleModule, AnsibleFailJson
from library import ns1_datasource

try:  # Python 3.3 +
    from unittest.mock import patch
except ImportError:
    from mock import patch

try:
    from ns1.rest.errors import ResourceException
except ImportError:
    # This is handled in NS1 module_utils
    pass


Response = namedtuple('Response', 'code')


@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.rest.data.Source.list")
def test_get_datasources(mock_source_list, ns1_config):
    zone_name = "test.zone"
    m = FakeAnsibleModule(zone_name)
    m.set_module_args({"apiKey": "testkey"})

    mock_source_list.return_value = [
        {"name": "one"}, {"name": "two"}, {"name": "three"}
    ]

    ds = ns1_datasource.NS1DataSources()
    datasources = ds.get_datasources()

    mock_source_list.assert_called_once_with()

    assert datasources == {
        "one": {"name": "one"},
        "two": {"name": "two"},
        "three": {"name": "three"},
    }


@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.rest.data.Source.list")
def test_get_datasources_failure(mock_source_list, ns1_config):
    zone_name = "test.zone"
    m = FakeAnsibleModule(zone_name)
    m.set_module_args({"apiKey": "testkey"})

    mock_source_list.side_effect = ResourceException(
        "fail", response=Response(500)
    )

    ds = ns1_datasource.NS1DataSources()

    with pytest.raises(AnsibleFailJson) as ex:
        ds.get_datasources()

    assert ex.value.args == ({
        "msg": "error code 500 - fail ", "failed": True
    },)

    mock_source_list.assert_called_once_with()
