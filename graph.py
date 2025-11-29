import plotly.graph_objects as go
import comparison_table_maker as tb_maker

def get_range_end(metric_name: str, table) -> int:
    """
    Searches the highest value within a given metric and returns it increased by 10% so that
    the highest bar doesn't hit the top (just a cosmetic thing)
    """
    values = table[metric_name]["orig_data"] + table[metric_name]["adapted_data"]
    max_val = max(values)
    return max_val + round(0.1*max_val)

def display_graph(table: dict) -> None:
    """
    Makes a bar graph that represents three metrics: level number, words and sentences amount

    Example of usage:
    >> display_graph(tb_maker.get_comparison_table("b2", False))
    """
    texts = [f"text {i}" for i in range(1, 11)]

    fig1 = go.Figure(data=[
        go.Bar(name="Original", x=texts, y=table["level_number"]["orig_data"], text=table["level_number"]["orig_data"]),
        go.Bar(name="Adapted", x=texts, y=table["level_number"]["adapted_data"], text=table["level_number"]["adapted_data"])
    ])
    fig2 = go.Figure(data=[
        go.Bar(name="Original", x=texts, y=table["words"]["orig_data"], text=table["words"]["orig_data"]),
        go.Bar(name="Adapted", x=texts, y=table["words"]["adapted_data"], text=table["words"]["adapted_data"])
    ])
    fig3 = go.Figure(data=[
        go.Bar(name="Original", x=texts, y=table["sentences"]["orig_data"], text=table["sentences"]["orig_data"]),
        go.Bar(name="Adapted", x=texts, y=table["sentences"]["adapted_data"], text=table["sentences"]["adapted_data"])
    ])

    fig1.update_layout(barmode='group', yaxis_range=[0, get_range_end("level_number", table)],
                       title="Уровень языка", title_font=dict(size=34))
    fig2.update_layout(barmode='group', yaxis_range=[0, get_range_end("words", table)],
                       title="Количество слов", title_font=dict(size=34))
    fig3.update_layout(barmode='group', yaxis_range=[0, get_range_end("sentences", table)],
                       title="Количество предложений", title_font=dict(size=34))
    fig1.show()
    fig2.show()
    fig3.show()

b1_table = tb_maker.get_comparison_table("b1")
b1_table_wo = tb_maker.get_comparison_table("b1", False)
b2_table = tb_maker.get_comparison_table("b1")
b2_table_wo = tb_maker.get_comparison_table("b1", False)
c1_table = tb_maker.get_comparison_table("b1",)
c2_table_wo = tb_maker.get_comparison_table("b1", False)
