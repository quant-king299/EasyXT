import pandas as pd

from data_manager.unified_data_interface import UnifiedDataInterface


class FakeDataAPI:
    def __init__(self, active_source='tdx', frame=None):
        self._active_source = active_source
        self.frame = frame
        self.connect_calls = 0
        self.price_kwargs = None

    def connect(self):
        self.connect_calls += 1
        self._active_source = 'eastmoney'
        return True

    def get_price(self, **kwargs):
        self.price_kwargs = kwargs
        return self.frame.copy()


def test_online_read_uses_injected_data_api_without_qmt_and_requests_raw_prices():
    api = FakeDataAPI(frame=pd.DataFrame({
        'date': [20260909, 20260910],
        'symbol': ['000001.SZ', '000001.SZ'],
        'open': [10.0, 10.1],
        'high': [10.2, 10.3],
        'low': [9.9, 10.0],
        'close': [10.1, 10.2],
        'volume': [1000, 1100],
        'amount': [1_010_000, 1_122_000],
        'source': ['TDX', 'TDX'],
    }))
    interface = UnifiedDataInterface(data_api=api)

    result = interface._read_from_online(
        '000001.SZ', '2026-09-09', '2026-09-10', '1d')

    assert api.connect_calls == 0
    assert api.price_kwargs == {
        'codes': ['000001.SZ'],
        'start': '2026-09-09',
        'end': '2026-09-10',
        'period': '1d',
        'count': None,
        'fields': ['open', 'high', 'low', 'close', 'volume', 'amount'],
        'adjust': 'none',
    }
    assert result.index.name == 'datetime'
    assert result.index.tolist() == [
        pd.Timestamp('2026-09-09'), pd.Timestamp('2026-09-10')]
    assert result.columns.tolist() == [
        'code', 'open', 'high', 'low', 'close', 'volume', 'amount']
    assert result['code'].tolist() == ['000001.SZ', '000001.SZ']


def test_online_source_connects_only_when_no_source_is_active():
    api = FakeDataAPI(active_source=None, frame=pd.DataFrame())
    interface = UnifiedDataInterface(data_api=api)

    assert interface._ensure_online_source() is True
    assert api.connect_calls == 1
    assert api._active_source == 'eastmoney'


def test_public_get_stock_data_uses_online_router_when_local_db_is_unavailable():
    api = FakeDataAPI(active_source='tdx', frame=pd.DataFrame({
        'date': ['2026-09-10'],
        'code': ['000001.SZ'],
        'open': [10.0],
        'high': [10.2],
        'low': [9.9],
        'close': [10.1],
        'volume': [1000],
        'amount': [1_010_000],
    }))
    interface = UnifiedDataInterface(data_api=api)
    interface.duckdb_available = False

    result = interface.get_stock_data(
        '000001.SZ', '2026-09-10', '2026-09-10',
        adjust='none', auto_save=False)

    assert len(result) == 1
    assert result.iloc[0]['close'] == 10.1
    assert api.price_kwargs['codes'] == ['000001.SZ']


def test_legacy_qmt_reader_name_delegates_to_data_api_router():
    api = FakeDataAPI(frame=pd.DataFrame({
        'time': pd.to_datetime(['2026-09-10']),
        'open': [10.0],
        'high': [10.2],
        'low': [9.9],
        'close': [10.1],
        'volume': [1000],
        'amount': [1_010_000],
    }))
    interface = UnifiedDataInterface(data_api=api)

    result = interface._read_from_qmt(
        '000001.SZ', '2026-09-10', '2026-09-10', '1d')

    assert len(result) == 1
    assert result.iloc[0]['code'] == '000001.SZ'
    assert api.price_kwargs['adjust'] == 'none'
