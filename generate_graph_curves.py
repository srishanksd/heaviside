"""Create self-contained SVG training/testing figures for the judges.

Run: python generate_graph_curves.py
No plotting package is required; files are written to graph_curves/.
"""

from pathlib import Path
import html
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "graph_curves"; OUT.mkdir(exist_ok=True)
VALIDATION_START = pd.Timestamp("2025-01-01"); WIDTH, HEIGHT = 1050, 620


def examples(frame, stations):
    index = {code: i for i, code in enumerate(stations)}; rows=[]; targets=[]; metadata=[]
    for station, group in frame.groupby("Station Code"):
        group=group.sort_values("Month").reset_index(drop=True); levels=group.groundwater_level.to_numpy(float)
        for i in range(12, len(group)):
            expected=pd.date_range(end=group.Month.iat[i]-pd.offsets.MonthBegin(1), periods=12, freq="MS")
            if not pd.DatetimeIndex(group.Month.iloc[i-12:i]).equals(expected): continue
            month=group.Month.iat[i].month; one=np.zeros(len(stations)); one[index[station]]=1
            rows.append(np.r_[[1,levels[i-1],levels[i-2],levels[i-3],levels[i-12],levels[i-1]-levels[i-2],levels[i-1]-levels[i-3],np.sin(2*np.pi*month/12),np.cos(2*np.pi*month/12)],one]); targets.append(levels[i]); metadata.append((station,group.Month.iat[i]))
    return np.asarray(rows),np.asarray(targets),pd.DataFrame(metadata,columns=["station","month"])


def frame(title, x_label, y_label, body, note=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img"><rect width="100%" height="100%" fill="#ffffff"/><text x="70" y="50" font-family="Arial" font-size="25" font-weight="700" fill="#082f49">{html.escape(title)}</text><text x="70" y="78" font-family="Arial" font-size="14" fill="#64748b">Chronological 2025 holdout unless noted</text><rect x="110" y="110" width="860" height="400" fill="#f8fafc" stroke="#cbd5e1"/>{body}<text x="540" y="570" text-anchor="middle" font-family="Arial" font-size="16" fill="#334155">{html.escape(x_label)}</text><text x="25" y="310" transform="rotate(-90 25 310)" text-anchor="middle" font-family="Arial" font-size="16" fill="#334155">{html.escape(y_label)}</text><text x="70" y="605" font-family="Arial" font-size="13" fill="#64748b">{html.escape(note)}</text></svg>'''


def line_svg(title, labels, series, y_label, note=""):
    labels = list(labels)
    values=np.concatenate([np.asarray(v,float) for _,v,_ in series]); lo,hi=float(values.min()),float(values.max()); pad=max((hi-lo)*.08,.1); lo-=pad;hi+=pad
    sx=lambda i:110+860*(i/max(len(labels)-1,1)); sy=lambda v:510-400*(v-lo)/(hi-lo)
    body=[]
    for fraction in np.linspace(0,1,5):
        v=lo+(hi-lo)*fraction; y=sy(v); body.append(f'<line x1="110" y1="{y:.1f}" x2="970" y2="{y:.1f}" stroke="#e2e8f0"/><text x="100" y="{y+5:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#64748b">{v:.2f}</text>')
    step=max(1,len(labels)//8)
    for i in range(0,len(labels),step): body.append(f'<text x="{sx(i):.1f}" y="535" text-anchor="middle" font-family="Arial" font-size="12" fill="#64748b">{html.escape(str(labels[i]))}</text>')
    for name,values,color in series:
        points=" ".join(f"{sx(i):.1f},{sy(v):.1f}" for i,v in enumerate(values)); body.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{points}"/><text x="{120+len(body)*155}" y="102" font-family="Arial" font-size="14" fill="{color}">● {html.escape(name)}</text>')
    return frame(title,"Month",y_label,"".join(body),note)


def scatter_svg(title, x, y, note):
    lo=min(x.min(),y.min());hi=max(x.max(),y.max());pad=max((hi-lo)*.06,.1);lo-=pad;hi+=pad; sx=lambda v:110+860*(v-lo)/(hi-lo);sy=lambda v:510-400*(v-lo)/(hi-lo)
    body=[f'<line x1="110" y1="510" x2="970" y2="110" stroke="#ef4444" stroke-dasharray="7 5"/>']
    body += [f'<circle cx="{sx(a):.1f}" cy="{sy(b):.1f}" r="2.2" fill="#087e8b" opacity=".35"/>' for a,b in zip(x,y)]
    return frame(title,"Actual groundwater level (m)","Predicted groundwater level (m)","".join(body),note)


def bars_svg(title, labels, values, y_label, colors, note=""):
    maximum=max(values)*1.15 or 1; width=760/max(len(labels),1); body=[]
    for i,(label,value) in enumerate(zip(labels,values)):
        h=400*value/maximum;x=150+i*width;body.append(f'<rect x="{x:.1f}" y="{510-h:.1f}" width="{width*.65:.1f}" height="{h:.1f}" fill="{colors[i%len(colors)]}"/><text x="{x+width*.32:.1f}" y="{500-h:.1f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">{value:.3f}</text><text x="{x+width*.32:.1f}" y="535" text-anchor="middle" font-family="Arial" font-size="11" fill="#64748b">{html.escape(str(label))}</text>')
    return frame(title,"Method / station",""+y_label,"".join(body),note)


data=pd.read_csv(ROOT/"prepared_dataset.csv");data["Station Code"]=data["Station Code"].astype(str).str.strip();data["Month"]=pd.to_datetime(data.Month);data=data.sort_values(["Station Code","Month"])
model=np.load(ROOT/"weights"/"station_aware_forecaster.npz",allow_pickle=False); stations=model["station_codes"].astype(str)
X,actual,meta=examples(data,stations);test_mask=meta.month.to_numpy()>=VALIDATION_START; persistence=X[:,1];prediction=persistence+float(model["blend_weight"])*(X@model["weights"]-persistence)
test=meta.loc[test_mask].copy();test["actual"]=actual[test_mask];test["prediction"]=prediction[test_mask];test["persistence"]=persistence[test_mask];test["error"]=test.actual-test.prediction

monthly=data.groupby("Month").size();(OUT/"01_data_coverage.svg").write_text(line_svg("Training data coverage by month",monthly.index.strftime("%b %Y"),[("records",monthly.values,"#087e8b")],"Station-month records","Input coverage and continuity check."),encoding="utf-8")
counts=data.groupby("Station Code").size();hist,bins=np.histogram(counts,bins=18);labels=[f"{bins[i]:.0f}–{bins[i+1]:.0f}" for i in range(len(hist))];(OUT/"02_station_history_distribution.svg").write_text(bars_svg("Training station-history distribution",labels,hist,"Stations",["#0ea5a8"],"Months per monitored station."),encoding="utf-8")
hist,bins=np.histogram(data[data.Month<VALIDATION_START].groundwater_level,bins=20);labels=[f"{bins[i]:.0f}" for i in range(len(hist))];(OUT/"03_training_target_distribution.svg").write_text(bars_svg("Training groundwater-level distribution",labels,hist,"Training records",["#2563eb"],"Distribution of the training target."),encoding="utf-8")
(OUT/"04_test_actual_vs_predicted.svg").write_text(scatter_svg("Testing: actual vs station-aware forecast",test.actual.to_numpy(),test.prediction.to_numpy(),"Dashed line = perfect forecast."),encoding="utf-8")
hist,bins=np.histogram(test.error,bins=24);labels=[f"{bins[i]:.1f}" for i in range(len(hist))];(OUT/"05_test_error_distribution.svg").write_text(bars_svg("Testing forecast-error distribution",labels,hist,"Forecasts",["#7c3aed"],"Error = actual − forecast."),encoding="utf-8")
monthly_mae=test.assign(abs_error=test.error.abs()).groupby("month").abs_error.mean();(OUT/"06_test_mae_by_month.svg").write_text(line_svg("Testing mean absolute error by month",monthly_mae.index.strftime("%b %Y"),[("MAE",monthly_mae.values,"#f97316")],"MAE (m)","Chronological validation behavior."),encoding="utf-8")
mae_model=float(np.mean(abs(test.actual-test.prediction)));mae_base=float(np.mean(abs(test.actual-test.persistence)));(OUT/"07_test_baseline_comparison.svg").write_text(bars_svg("Testing MAE: deployed model vs persistence",["Persistence","Station-aware"],[mae_base,mae_model],"MAE (m)",["#94a3b8","#16a34a"],"Lower is better."),encoding="utf-8")
station_mae=test.assign(abs_error=test.error.abs()).groupby("station").abs_error.mean().nlargest(15).sort_values(ascending=False);(OUT/"08_test_highest_station_mae.svg").write_text(bars_svg("Testing: stations with highest forecast MAE",station_mae.index,station_mae.values,"MAE (m)",["#dc2626"],"Focus stations for field verification and model improvement."),encoding="utf-8")
representative=test.groupby("station").size().nlargest(3).index;subset=test[test.station.isin(representative)];series=[]
for station in representative:
    g=subset[subset.station==station].sort_values("month");series.extend([(f"{station} observed",g.actual.values,"#087e8b"),(f"{station} forecast",g.prediction.values,"#f97316")])
labels=sorted(subset.month.unique()); values=[]
for _,v,_ in series: values.append(v)
# Use a single representative station to keep the line chart readable.
g=test[test.station==representative[0]].sort_values("month");(OUT/"09_test_station_trend.svg").write_text(line_svg(f"Testing: observed vs forecast — station {representative[0]}",g.month.dt.strftime("%b %Y"),[("Observed",g.actual.values,"#087e8b"),("Forecast",g.prediction.values,"#f97316")],"Groundwater level (m)","Representative monitored-station testing series."),encoding="utf-8")
report={"validation_period":"2025-01 through 2025-12","test_samples":int(len(test)),"station_aware_mae_m":mae_model,"persistence_mae_m":mae_base,"charts":9}
(OUT/"README.txt").write_text("Judge-facing training/testing graph set\n\n"+json.dumps(report,indent=2)+"\n\nAll testing charts use a chronological 2025 holdout.\n",encoding="utf-8");print(json.dumps(report,indent=2))
