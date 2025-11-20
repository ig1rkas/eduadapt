from bert_score import score

import pandas as pd
import numpy as np

# Считывание данных из файла
df = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/texts.csv')

orig_texts = df['Текст без терминов'].dropna().tolist()
adapted_B1 = df['Адаптированный текст(B1) без терминов'].dropna().tolist()
adapted_B2 = df['Адаптированный текст(B2) без терминов'].dropna().tolist()
adapted_C1 = df['Адаптированный текст(С1) без терминов'].dropna().tolist()

orig_texts_terms = df['Исходные тексты с терминами'].dropna().tolist()
adapted_B1_terms = df['Адаптированный текст(B1) с терминами'].dropna().tolist()
adapted_B2_terms = df['Адаптированный текст(B2) с терминами'].dropna().tolist()
adapted_C1_terms = df['Адаптированный текст(С1) с терминами'].dropna().tolist()

def estimation(cands, refs):
  P, R, F1 = score(cands, refs, lang="ru", verbose=True, model_type="bert-base-multilingual-cased")
  mean_P = P.mean().item()
  mean_R = R.mean().item()
  mean_F1 = F1.mean().item()
  return mean_P, mean_R, mean_F1

estim1 = estimation(adapted_B1_terms, orig_texts_terms) # оценка сохранения смысла в адаптированных текстах уровня B1 с терминами
estim2 = estimation(adapted_B2_terms, orig_texts_terms) # оценка сохранения смысла в адаптированных текстах уровня B2 с терминами
estim3 = estimation(adapted_C1_terms, orig_texts_terms) # оценка сохранения смысла в адаптированных текстах уровня C1 с терминами
estim4 = estimation(adapted_B1, orig_texts) # оценка сохранения смысла в адаптированных текстах уровня B1 без терминов
estim5 = estimation(adapted_B2, orig_texts) # оценка сохранения смысла в адаптированных текстах уровня B2 без терминов
estim6 = estimation(adapted_C1, orig_texts) # оценка сохранения смысла в адаптированных текстах уровня C1 без терминов

# Построение таблицы сравнения
df = pd.DataFrame({
    'Percision_estim1': estim1[0],
    'Recall_estim1': estim1[1],
    'F1_score_estim1': estim1[2],
    'Percision_estim2': estim2[0],
    'Recall_estim2': estim2[1],
    'F1_score_estim2': estim2[2],
    'Percision_estim3': estim3[0],
    'Recall_estim3': estim3[1],
    'F1_score_estim3': estim3[2],
    'Percision_estim4': estim4[0],
    'Recall_estim4': estim4[1],
    'F1_score_estim4': estim4[2],
    'Percision_estim5': estim5[0],
    'Recall_estim5': estim5[1],
    'F1_score_estim5': estim5[2],
    'Percision_estim6': estim6[0],
    'Recall_estim6': estim6[1],
    'F1_score_estim6': estim6[2],
}, index=['value'])

df

result = df

result

comparison = pd.DataFrame({
    'estimations': ['estim1', 'estim2', 'estim3', 'estim4', 'estim5', 'estim6'],
    'Precision': result.iloc[0, ::3].to_list(),
    'Recall': result.iloc[0, 1::3].to_list(),
    'F1_score': result.iloc[0, 2::3].to_list()
})

print(comparison)

# Построение диаграмм
import plotly.graph_objects as go
animals=comparison['estimations']

fig = go.Figure(data=[
  go.Bar(name='Precision', x=animals, y=comparison['Precision'], text=round(comparison['Precision'], 3), textposition='outside', marker_color='#e9b872'),
  go.Bar(name='Recall', x=animals, y=comparison['Recall'], text=round(comparison['Recall'], 3), textposition='outside', marker_color='#a63d40'),
  go.Bar(name='F1_score', x=animals, y=comparison['F1_score'], text=round(comparison['F1_score'], 3), textposition='outside', marker_color='#808080'),
])
# Change the bar mode
fig.update_layout(barmode='group', yaxis_range=[0.6, 1], width=2000)
fig.show()