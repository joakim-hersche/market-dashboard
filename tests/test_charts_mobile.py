"""Tests for mobile chart overrides in src.charts."""
import plotly.graph_objects as go

from src.charts import _mobile_overrides


def test_mobile_overrides_sets_dragmode_false():
    fig = go.Figure()
    _mobile_overrides(fig)
    assert fig.layout.dragmode is False


def test_mobile_overrides_sets_hovermode_closest():
    fig = go.Figure()
    _mobile_overrides(fig)
    assert fig.layout.hovermode == "closest"


def test_mobile_overrides_sets_tick_font_size():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2]))
    _mobile_overrides(fig)
    assert fig.layout.xaxis.tickfont.size == 9
    assert fig.layout.yaxis.tickfont.size == 9


def test_mobile_overrides_sets_hoverlabel_font_size():
    fig = go.Figure()
    _mobile_overrides(fig)
    assert fig.layout.hoverlabel.font.size == 10


def test_mobile_overrides_hides_axis_titles():
    fig = go.Figure()
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Price")
    _mobile_overrides(fig)
    assert fig.layout.xaxis.title.text is None
    assert fig.layout.yaxis.title.text is None
