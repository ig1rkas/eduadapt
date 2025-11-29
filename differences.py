import pandas as pd
import comparison_table_maker as tb_maker


def make_differences_table(level: str, with_t=True):
    """
    Generates table displaying differences in metrics of all texts
    Every cell shows how much the original value decreased
    Thence, negative value means that it increased

    Example of usage:
    print(make_differences_table("b2", False))
    """
    comp_table = tb_maker.get_comparison_table(level, with_t)
    diff_table = dict()
    for text_number in range(10):
        text = f"Text {text_number+1}"
        diff_table[text] = [
            comp_table["level_number"]["orig_data"][text_number] -
            comp_table["level_number"]["adapted_data"][text_number],

            comp_table["words"]["orig_data"][text_number] -
            comp_table["words"]["adapted_data"][text_number],

            comp_table["sentences"]["orig_data"][text_number] -
            comp_table["sentences"]["adapted_data"][text_number]
        ]
    df = pd.DataFrame(
        diff_table,
        index=[
            comp_table["level_number"]["metric_name"],
            comp_table["words"]["metric_name"],
            comp_table["sentences"]["metric_name"]
        ]
    )
    return df

