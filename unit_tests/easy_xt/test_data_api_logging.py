import logging

from easy_xt.data_api import _log_missing_qmt_history


def test_missing_history_uses_one_actionable_log_record(caplog):
    with caplog.at_level(logging.WARNING, logger='easy_xt.data_api'):
        _log_missing_qmt_history(['000001.SZ'])

    records = [record for record in caplog.records
               if record.name == 'easy_xt.data_api']
    assert len(records) == 1
    assert '000001.SZ' in records[0].getMessage()
    assert 'TROUBLESHOOTING.md' in records[0].getMessage()
