import pytest
import ns1.records
import ns1.zones

from .common import FakeAnsibleModule, AnsibleExitJson
from library import ns1_record

try:  # Python 3.3 +
    from unittest.mock import patch
except ImportError:
    from mock import patch


ZONE = "test.zone"
DOMAIN = "www.test.zone"


def set_record_args(**kwargs):
    """Sets module args for an A record in ZONE, overridden by kwargs

    :param kwargs: args to add to or override in the module args
    :type kwargs: dict
    """
    args = {
        "apiKey": "testkey",
        "name": DOMAIN,
        "zone": ZONE,
        "type": "A",
        "answers": [{"answer": ["1.2.3.4"]}],
    }
    args.update(**kwargs)
    FakeAnsibleModule.set_module_args(args)


def get_record_data(**kwargs):
    """Returns mock record data as returned by the API, updated with kwargs

    :param kwargs: args to add to or override in the record data
    :type kwargs: dict
    :return: Dict of record data
    :rtype: dict
    """
    data = {
        "id": "abc123",
        "zone": ZONE,
        "domain": DOMAIN,
        "type": "A",
        "answers": [{"answer": ["1.2.3.4"]}],
        "filters": [],
        "ttl": 3600,
        "use_client_subnet": True,
        "meta": {},
        "regions": {},
        "feeds": [],
    }
    data.update(**kwargs)
    return data


def build_record(ns1_config, **record_data):
    """Returns a mock SDK record object populated with record_data

    :param ns1_config: Mock NS1 SDK config object
    :type ns1_config: Config
    :param record_data: args to add to or override in the record data
    :type record_data: dict
    :return: Mock SDK record object
    :rtype: ns1.records.Record
    """
    zone = ns1.zones.Zone(ns1_config, ZONE)
    record = ns1.records.Record(zone, DOMAIN, "A")
    record.data = get_record_data(**record_data)
    return record


@pytest.mark.usefixtures("mock_module_helper")
def test_filter_empty_subparams_list_of_scalars():
    set_record_args(blocked_tags=["env", "team"])
    r = ns1_record.NS1Record()
    assert r.filter_empty_subparams("blocked_tags") == ["env", "team"]


@pytest.mark.usefixtures("mock_module_helper")
def test_api_params_includes_tags():
    set_record_args(tags={"env": "prod"}, blocked_tags=["team"])
    r = ns1_record.NS1Record()
    params = r.api_params()
    assert params["tags"] == {"env": "prod"}
    assert params["blocked_tags"] == ["team"]


@pytest.mark.usefixtures("mock_module_helper")
def test_api_params_omits_unset_tags():
    set_record_args()
    r = ns1_record.NS1Record()
    params = r.api_params()
    assert "tags" not in params
    assert "blocked_tags" not in params


@pytest.mark.usefixtures("mock_module_helper")
def test_sanitize_record_preserves_tag_named_id():
    set_record_args()
    r = ns1_record.NS1Record()
    record = r.sanitize_record(get_record_data(tags={"id": "cmdb-42"}))
    # the record's own ID is dropped from the diff, a tag called "id" is not
    assert "id" not in record
    assert record["tags"] == {"id": "cmdb-42"}


@pytest.mark.parametrize(
    "record_data,module_args,exp_changed,exp_args",
    [
        pytest.param(
            {},
            {"tags": {"env": "prod"}},
            True,
            {"tags": {"env": "prod"}},
            id="tags_added_to_untagged_record",
        ),
        pytest.param(
            {"tags": {"env": "dev"}},
            {"tags": {"env": "prod"}},
            True,
            {"tags": {"env": "prod"}},
            id="tag_value_updated",
        ),
        pytest.param(
            {"tags": {"env": "prod", "team": "netops"}},
            {"tags": {"env": "prod"}},
            True,
            {"tags": {"env": "prod"}},
            id="tag_key_removed",
        ),
        pytest.param(
            {"tags": {"env": "prod"}},
            {"tags": {}},
            True,
            {"tags": {}},
            id="tags_cleared",
        ),
        pytest.param(
            {"tags": {"env": "prod"}},
            {"tags": {"env": "prod"}},
            False,
            None,
            id="no_tag_diff",
        ),
        pytest.param(
            {}, {"tags": {}}, False, None, id="no_tags_either_side",
        ),
        pytest.param(
            {"tags": {"env": "prod"}}, {}, False, None, id="tags_unmanaged",
        ),
        pytest.param(
            {},
            {"blocked_tags": ["env"]},
            True,
            {"blocked_tags": ["env"]},
            id="blocked_tags_added",
        ),
        pytest.param(
            {"blocked_tags": ["env", "team"]},
            {"blocked_tags": ["env"]},
            True,
            {"blocked_tags": ["env"]},
            id="blocked_tags_purged",
        ),
        pytest.param(
            {"blocked_tags": ["env"]},
            {"blocked_tags": ["team"], "record_mode": "append"},
            True,
            {"blocked_tags": ["env", "team"]},
            id="blocked_tags_appended",
        ),
        pytest.param(
            {"blocked_tags": ["env"]},
            {"blocked_tags": ["env"], "record_mode": "append"},
            False,
            None,
            id="no_blocked_tags_diff_in_append_mode",
        ),
    ],
)
@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.records.Record.update")
def test_update_tags(
    mock_record_update,
    ns1_config,
    record_data,
    module_args,
    exp_changed,
    exp_args,
):
    set_record_args(**module_args)
    record = build_record(ns1_config, **record_data)

    r = ns1_record.NS1Record()
    with pytest.raises(AnsibleExitJson) as result:
        r.update(record)

    assert result.value.args[0]["changed"] == exp_changed
    if exp_changed:
        mock_record_update.assert_called_once()
        called_args = mock_record_update.call_args[1]
        for key, val in exp_args.items():
            assert called_args[key] == val
    else:
        mock_record_update.assert_not_called()


@pytest.mark.usefixtures("mock_module_helper")
@patch("ns1.records.Record.update")
def test_update_tags_in_check_mode(mock_record_update, ns1_config):
    set_record_args(tags={"env": "prod"})
    record = build_record(ns1_config)

    r = ns1_record.NS1Record()
    r.module.check_mode = True
    with pytest.raises(AnsibleExitJson) as result:
        r.update(record)

    assert result.value.args[0]["changed"] is True
    mock_record_update.assert_not_called()
