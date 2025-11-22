import pandas as pd

# the file is to be updated in case new adaptation data appears
df = pd.read_csv("analysisResults.csv")

# only relevant ones; may be extended manually if needed
metrics = [
    "level_number",
    "words",
    "sentences"
]

def get_metric(metric: str, level: str, with_t: bool):
    """
    Transforms and returns metric_name to the form used by the source csv file.
    For example: sentences -> sentences_b1txt_wo_terms
    """
    if with_t:
        return metric + '_' + level + 'txt'
    else:
        return metric + '_' + level + 'txt_wo_terms'


def get_comparison_table(level: str, with_t=True) -> dict:
    """
    Makes and returns the table containing data about different metrics of all texts.
    Table view:
    {
        "level_number": {
            "metric_name": ...,
            "orig_data": [x1, x2, ...],
            "adapted_data": [y1, y2, ...],
        },
        "words": {
            "metric_name": ...,
            "orig_data": [x1, x2, ...],
            "adapted_data": [y1, y2, ...],
        },
        "sentences": {
            "metric_name": ...,
            "orig_data": [x1, x2, ...],
            "adapted_data": [y1, y2, ...],
        }
    }
    """
    table = dict()
    for m in metrics:
        metric_for_orig = get_metric(m, "orig", with_t)
        metric_for_adapted = get_metric(m, level, with_t)

        orig_data = tuple(df[metric_for_orig])
        adapted_data = tuple(df[metric_for_adapted])

        table[m] = {
            "metric_name": m,
            "orig_data": orig_data,
            "adapted_data": adapted_data
        }
    return table
