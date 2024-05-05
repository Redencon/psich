import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from dash import html, Input, Output, callback, dcc, Dash
import pandas as pd
from sql_base import DatabaseManager, DATE_FORMAT
from sql_classes import *
from datetime import date, timedelta
import os
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import json

# --- [ Constants ] ---
cash_dir = "dash_precalc"
bots = ["nastya", "diana"]
dbms = {bot: DatabaseManager(f"{bot}.sqlite") for bot in bots}
score_map = ["Замечательно", "Отлично", "Хорошо", "Нормально", "Не очень", "Тяжело", "Трудно"]
# colors = ["#71F582", "#F5B371", "#71F5CD", "#F58D71", "#7FA197", "#637565", "#756C63"]
colors = ["#E42627", "#E38300", "#FED902", "#00AD00", "#0058D1", "#AC28FE", "#7F4C26"]
color_map_i = {i: color for i, color in enumerate(colors)}
color_map_s = {score_map[i]: color for i, color in enumerate(colors)}

# --- [ Data Preparations ] ---
def today() -> str:
  return date.today().strftime(DATE_FORMAT)

def date_range(start: date, end: date) -> list[str]:
  dates = []
  while start <= end:
    dates.append(start.strftime(DATE_FORMAT))
    start += timedelta(days=1)
  return dates

def get_filtered_data(
  bot: str = "nastya",
  tpe: str = "mood",
  drange: list[str]|None = None,
  ps: str|None = None,
  sex: str|None = None,
  year: str|None = None
):
  if drange is None:
    drange = date_range(
      date.today() - timedelta(days=7), date.today()
    )
  statement = (
    select(Response)
    .where(Response.date.in_(drange))
    .where(Response.tpe == tpe)
    .join(Meta, Meta.uid == Response.uid)
    .distinct()
  )
  if ps:
    statement = (
      statement
      .where(Meta.key=="demog.ps", Meta.value == ps)
    )
  if sex:
    statement = (
      statement
      .where(Meta.key=="demog.sex", Meta.value == sex)
    )
  if year:
    statement = (
      statement
      .where(Meta.key=="demog.year", Meta.value == year)
    )
  with Session(dbms[bot].engine) as session:
    responses = session.scalars(statement).all()
  df = pd.DataFrame([
    {
      "date": response.date,
      "time": response.time,
      "score": response.score
    }
    for response in responses
  ], columns=['date', 'time', 'score'])
  try:
    df['date'] = pd.to_datetime(df['date'])
  except KeyError:
    raise KeyError(f"Key not found?! colomns: {' '.join(df.columns)}\n{responses=}")
  return df

def get_completion_array(bot: str, dates: list[str]):
  with Session(dbms[bot].engine) as session:
    result = (
      session.query(func.count(Response.uid), Response.date)
      .where(Response.date.in_(dates))
      .group_by(Response.date)
    ).all()
  df = pd.DataFrame([
    {"date": d, "count": c}
    for c, d in result
  ])
  df['date'] = pd.to_datetime(df['date'])
  return df

def get_frequencies(df: pd.DataFrame, normalize: bool):
  df1 = df.groupby(["date", "score"]).count().reset_index()
  df2 = df.groupby(["date"]).count().reset_index()
  df3 = pd.merge(df1, df2, "outer", on="date")
  by = df3["time_y"] if normalize else df3["time_y"].max()
  df3["ratio"] = df3["time_x"] / by
  df3["count"] = df3["time_x"]
  df3["score"] = df3["score_x"]
  df3 = df3[["date", "score", "ratio", "count"]]
  df3["score"] = df3["score"].apply(lambda i: score_map[i])
  df3.sort_values("score", ascending=False, inplace=True)
  return df3

def get_date_counts(
  date: date,
  bot: str = "nastya",
  tpe: str = "mood",
  ps: str|None = None,
  sex: str|None = None,
  year: str|None = None
):
  drange = date_range(date, date)
  return get_filtered_data(bot, tpe, drange, ps, sex, year)

def get_demog_data(bot: str = "nastya"):
  demog_keys = ["demog.ps", "demog.sex", "demog.year"]
  df = pd.DataFrame(columns=["key", "value", "count"])
  with Session(dbms[bot].engine) as session:
    for key in demog_keys:
      result = (
        session.query(Meta.value, func.count(Meta.value))
        .where(Meta.key == key)
        .group_by(Meta.value)
      ).all()
      df = pd.concat([
        df, pd.DataFrame([
          {"key": key[6:], "value": value, "count": count}
          for value, count in result
        ])
      ])
  return df

def clean_demog_data(df: pd.DataFrame):
  def value_fix(v: str):
    if v == "Male":
      return "Мужской"
    if v == "Female":
      return "Женский"
    if v == "Another":
      return "Другое"
    if v == "Другой":
      return "Другое"
    if v == "18-21":
      return "Не студент"
    if v == "22-28":
      return "Не студент"
    if v == "Moscow":
      return "Другое"
    if v == "Russia":
      return "Другое"
    return v
  df['value'] = df['value'].apply(value_fix)
  return df

def get_poll_times(bot: str = "nastya", tpe: str = "mood"):
  with Session(dbms[bot].engine) as session:
    times = session.scalars(
      select(Poll.time)
      .where(Poll.tpe == tpe)
    ).all()
  def time_str_to_int(ts: str):
    h, m = ts.split(":")
    return int(h) * 60 + int(m)
  return [time_str_to_int(t) for t in times]

def get_answer_times(bot:str):
  with Session(dbms[bot].engine) as session:
    times = session.scalars(select(Response.time)).all()
  def time_str_to_int(ts: str):
    h, m = ts.split(":")
    return int(h) * 60 + int(m)
  return [time_str_to_int(t) for t in times]


# --- [ Layout ] ---
app = Dash("PSI-dash", external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], title="PSI Data")

app.layout = html.Div([
  html.Header([
    html.H1(children="PSI bots data", style={"textAlign": "left"}),
    html.H4(children="made by Folegle", style={"textAlign": "left"},)
  ], style={'margin-left': "30%", 'margin-right': "30%"}),
  html.Div([
    html.P("Choose bot"),
    dcc.Dropdown([
      {'label': 'Nastyenka', 'value': 'nastya'},
      {'label': 'Diana', 'value': 'diana'}
    ], value = 'nastya', id='bot_choice'),
    dcc.Interval(id="interval-refresh", interval=5*60*1000, n_intervals=0),
], style={'margin-left': "30%", 'margin-right': "30%"}),
  html.Div([
    dcc.Graph("today-distribution"),
  ], style={'margin-left': "30%", 'margin-right': "30%"}),
  html.Div([
    html.Div(
      dcc.Graph(id="demog-sex-dist")
    , style={'padding': 10, 'flex': 1}),
    html.Div(
      dcc.Graph(id="demog-ps-dist")
    , style={'padding': 10, 'flex': 1}),
    html.Div(
      dcc.Graph(id="demog-year-dist")
    , style={'padding': 10, 'flex': 1})
  ], style={'display': 'flex', 'flexDirection': 'row'}),
  html.Br(),
  html.Div([
    html.H2("Additional data"),
    html.P("Choose date range"),
    html.Div([
      dcc.DatePickerRange(date.today() - timedelta(days=7), date.today(), id="date_range"),
      dcc.Checklist(["Normalize daily answers"], id="dans_norm")
    ], style={'flex': 1}),
    ], style={'margin-left': "30%", 'margin-right': "30%"}),
  html.Div([
    html.Div([
      dcc.Graph(id="poll-times-plot"),
      dcc.Graph(id="answer-times-plot"),
    ], style={'padding': 10, 'flex': 1}),
    html.Div([
      dcc.Graph("completion-plot"),
      dcc.Graph("quantile-plot")
    ], style={'padding': 10, 'flex': 1}),
  ], style={'display': 'flex', 'flexDirection': 'row'}),
  html.Footer([
    html.Small("Made by Folegle — MKI-MIPT SC Digital Architect and Analyst")
  ])
])

# --- [ Callbacks ] ---
@callback(
  Output("poll-times-plot", "figure"),
  Input("bot_choice", "value")
)
def build_poll_times(*_):
  data1 = get_answer_times("nastya")
  data2 = get_answer_times("diana")
  fig = ff.create_distplot(
    [data1, data2],
    ["Nastyenka", "Diana"],
    show_hist=False, colors=['#F5AB26', '#2A5D8E'],
    bin_size=60)
  fig.update_xaxes(
    ticktext=[f"{i*3:0>2}:00" for i in range(9)],
    tickvals=[i*180 for i in range(9)],
    range=[0, 24*60]
  )
  return fig


@callback(
  Output("answer-times-plot", "figure"),
  Input("bot_choice", "value")
)
def build_answer_times(*_):
  data1 = get_poll_times("nastya")
  data2 = get_poll_times("diana")
  fig = ff.create_distplot(
    [data1, data2],
    ["Nastyenka", "Diana"],
    show_curve=False, colors=['#F5AB26', '#2A5D8E'],
    bin_size=60)
  fig.update_xaxes(
    ticktext=[f"{i*3:0>2}:00" for i in range(9)],
    tickvals=[i*180 for i in range(9)],
    range=[0, 24*60]
  )
  return fig


@callback(
  Output("demog-sex-dist", "figure"),
  Output("demog-ps-dist", "figure"),
  Output("demog-year-dist", "figure"),
  Input("bot_choice", "value"),
  Input("demog-sex-dist", "clickData"),
  Input("demog-ps-dist", "clickData"),
  Input("interval-refresh", "n_intervals"),
)
def build_demog(bot_choice, cd1, cd2, _):
  df = get_demog_data(bot_choice)
  df = clean_demog_data(df)
  df1 = df[df['key'] == 'sex']
  df2 = df[df['key'] == 'ps']
  df3 = df[df['key'] == 'year']
  if cd1:
    df1['a'] = (df1['value'] == cd1['points'][0]['label']).apply(lambda b: 0.2 if b else 0.)
  else:
    df1['a'] = df1['value'].apply(lambda _: 0)
  if cd2:
    df2['a'] = (df2['value'] == cd2['points'][0]['label']).apply(lambda b: 0.2 if b else 0.)
  else:
    df2['a'] = df2['value'].apply(lambda _: 0)
  fig_1 = go.Figure(go.Pie(values=df1['count'], labels=df1['value'], pull = df1['a']))
  fig_2 = go.Figure(go.Pie(values=df2['count'], labels=df2['value'], pull = df2['a']))
  fig_3 = px.pie(df3, values='count', names='value', category_orders={'value': [
    "1", "2", "3", "4", "5", "6", "7+", "Не студент"
  ]})
  for fig in (fig_1, fig_2, fig_3):
    fig.update_layout(clickmode='event+select')
  return fig_1, fig_2, fig_3



@callback(
  Output("completion-plot", "figure"),
  Output("quantile-plot", "figure"),
  Input("bot_choice", "value"),
  Input("date_range", "start_date"),
  Input("date_range", "end_date"),
  Input("dans_norm", "value"),
  Input("interval-refresh", "n_intervals")
)
def build_ranged_plots(bot_choice, start_date, end_date, dans_norm, _):
  start = date.fromisoformat(start_date)
  end = date.fromisoformat(end_date)
  drange = date_range(start, end)
  completion = get_completion_array(bot_choice, drange)
  freqs = get_frequencies(get_filtered_data(bot_choice, drange=drange), bool(dans_norm))
  fig1 = px.bar(completion, "date", "count")
  fig2 = px.bar(
    freqs, 'date', 'ratio', 'score',
    color_discrete_map=color_map_s, category_orders={'score': score_map[::-1]})
  fig2.update_layout(legend={'traceorder': 'reversed'})
  return fig1, fig2


@callback(
  Output("today-distribution", "figure"),
  Input("bot_choice", "value"),
  Input("interval-refresh", "n_intervals")
)
def build_today(bot_choice, _):
  df = get_filtered_data(bot_choice, drange=[today()])
  if len(df) == 0:
    fig = go.Figure().add_annotation(
      x=2, y=2, text="No Data to Display",
      font=dict(family="sans serif", size=25, color="crimson"),
      showarrow=False, yshift=10)
  fig = px.histogram(df, x='score', color='score', color_discrete_map=color_map_i)
  fig.update_xaxes(
    ticktext = score_map,
    tickvals=[i for i in range(7)]
  )
  fig.update_layout(showlegend=False)
  return fig


# --- [ RUN ] ---
if __name__ == "__main__":
  app.run(debug=True)
