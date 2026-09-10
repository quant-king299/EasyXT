import pandas as pd

from easy_xt.fallback_fetcher import FallbackFetcher


def test_fallback_order_matches_data_api(monkeypatch):
    fetcher = FallbackFetcher(qmt_api=object(), tdx_provider=object())
    calls = []

    monkeypatch.setattr(fetcher, '_try_qmt',
                        lambda *args: calls.append('qmt') or None)
    monkeypatch.setattr(fetcher, '_try_tdx',
                        lambda *args: calls.append('tdx') or None)
    monkeypatch.setattr(fetcher, '_try_eastmoney',
                        lambda *args: calls.append('eastmoney') or
                        pd.DataFrame({'close': [1]}))

    result = fetcher.fetch('000001.SZ')
    assert not result.empty
    assert calls == ['qmt', 'tdx', 'eastmoney']


def test_remote_xtquant_is_labelled_xqshare(monkeypatch):
    class RemoteAPI:
        _active_source = 'xqshare'

        def get_price(self, **_kwargs):
            return pd.DataFrame({'close': [1]})

    fetcher = FallbackFetcher(qmt_api=RemoteAPI())
    result = fetcher.fetch('000001.SZ')

    assert result.loc[0, 'source'] == 'XQSHARE'
    assert fetcher.get_stats()['success_by_source'] == {'XQSHARE': 1}
