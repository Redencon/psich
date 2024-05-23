from matplotlib.colors import LinearSegmentedColormap
from statsmodels.nonparametric.smoothers_lowess import lowess
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sql_base import DatabaseManager

hex_colors = ["#E42627", "#E38300", "#FED902", "#00AD00", "#0058D1", "#AC28FE", "#7F4C26"][::-1]
n_colors = len(hex_colors)
positions = np.linspace(0, 1, n_colors)
colorscale = [[pos, color] for pos, color in zip(positions, hex_colors)]
color_map_i = {i+1: color for i, color in enumerate(hex_colors)}

cmap_name = 'my_continuous_cmap'
continuous_cmap = LinearSegmentedColormap.from_list(cmap_name, hex_colors)
del cmap_name, positions, n_colors

def user_graph(dbm:DatabaseManager, uid:int, username:str, start:str, end:str, smoothness:float=0.15):
    RANGE = pd.date_range(start, end)
    d = dbm.get_user_calendar(uid, "mood")
    df = pd.DataFrame([{'date': k, 'score': v} for k, v in d.items()])
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'].isin(RANGE)]
    df['score'] = 7 - df['score']
    del d
    
    SM_RANGE = pd.date_range(df['date'].min(), df["date"].max(), freq='3h')
    
    a = lowess(df['score'], df['date'], smoothness, xvals=SM_RANGE)
    line_df = pd.DataFrame([{'date': d, 'score': s} for d, s in zip(SM_RANGE, a)])
    line_df['color'] = line_df['score'].apply(lambda s: "rgb({},{},{})".format(*[int(c*255)for c in continuous_cmap((s-1)/6)]))
    sl = line_df['score'].to_list()
    cl = line_df['color'].to_list()
    dl = line_df['date'].to_list()
    segments = pd.DataFrame([{'x1': s1, 'x2': s2, 'y1': d1, 'y2': d2, 'color': c} for s1, s2, c, d1, d2 in zip(sl[:-1], sl[1:], cl[1:], dl[:-1], dl[1:])])
    del sl, cl, dl
    
    fig = px.scatter(
        df, x='date', y='score', color='score',
        color_continuous_scale=colorscale, range_color=(1, 7),
        title="Mood graph of user {}".format(username)
    )
    fig.add_traces([
        go.Scatter(y=[row.x1, row.x2], x=[row.y1, row.y2], line_color=row.color, mode='lines', showlegend=False)
        for row in segments.itertuples()
    ])
    filename = "assets/{}.png".format(uid)
    with open(filename, 'wb') as f:
        f.write(fig.to_image(format="png", scale=2))
    return filename