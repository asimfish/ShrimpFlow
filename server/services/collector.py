"""数据采集占位模块。

实际采集与事件处理逻辑在 real_data_collector.py 与 routes/collector.py 中实现。
"""


def process_raw_event(raw_event):
    """处理原始事件数据；当前由 real_data_collector 等模块承担。"""
    pass


def enrich_event(event):
    """为事件添加语义信息；当前由 real_data_collector 等模块承担。"""
    pass
