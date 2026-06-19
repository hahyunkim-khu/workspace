import warnings
warnings.filterwarnings('ignore')

import os, sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# ── 한글 폰트 등록 ──────────────────────────────────────────
import shutil
_src_dir = os.path.join(os.path.dirname(sys.executable),
                        'lib/python3.14/site-packages/koreanize_matplotlib/fonts')
_mpl_font_dir = os.path.join(os.path.dirname(matplotlib.__file__),
                              'mpl-data', 'fonts', 'ttf')
for _fname in ['NanumGothic.ttf', 'NanumGothicBold.ttf']:
    _src = os.path.join(_src_dir, _fname)
    if os.path.exists(_src):
        shutil.copy(_src, os.path.join(_mpl_font_dir, _fname))

_cache_dir = matplotlib.get_cachedir()
for _f in os.listdir(_cache_dir):
    try: os.remove(os.path.join(_cache_dir, _f))
    except: pass
fm._load_fontmanager(try_read_cache=False)

matplotlib.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.figsize']      = (13, 5)
sns.set_style('whitegrid')
plt.rcParams['font.family']         = 'NanumGothic'
print("✓ Setup complete (NanumGothic)")

# ── 출력 디렉토리 ────────────────────────────────────────────
OUT = '../output_images'
os.makedirs(OUT, exist_ok=True)

def save(name):
    path = os.path.join(OUT, name)
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  saved → {name}")

# ═══════════════════════════════════════════════════════════
# 0. 데이터 로딩
# ═══════════════════════════════════════════════════════════
DATA_DIR = '../data'

df = pd.read_csv(
    f'{DATA_DIR}/member_deidentified/member_export_2026-03-01_to_2026-06-15_004713.csv',
    low_memory=False
)
df['최초 가입일'] = pd.to_datetime(df['최초 가입일'], errors='coerce')
df['가입 승인']  = pd.to_datetime(df['가입 승인'],  errors='coerce')
print(f"멤버 데이터: {df.shape[0]:,}명 × {df.shape[1]}컬럼")

def get_models(df):
    models, seen = [], set()
    for c in df.columns:
        for sfx in [' Input 크레딧', ' Output 크레딧', ' 웹검색 크레딧']:
            if c.endswith(sfx):
                name = c[: -len(sfx)]
                if name.startswith('None') or '.' in name.split(' ')[-1]:
                    break
                if name not in seen:
                    seen.add(name)
                    models.append(name)
                break
    return models

MODELS = get_models(df)
CREDIT = '기간 내 크레딧 사용량 총합'

def model_credit_sum(df_sub, model):
    cols = [c for c in df_sub.columns
            if (c.startswith(model + ' ') and
                any(c.endswith(s) for s in [' Input 크레딧', ' Output 크레딧', ' 웹검색 크레딧']) and
                not c.split()[-1].replace('.','').isdigit())]
    return df_sub[cols].fillna(0).sum(axis=1)

# ═══════════════════════════════════════════════════════════
# 1. 크레딧 사용량 분포
# ═══════════════════════════════════════════════════════════
print("\n[1] 크레딧 분포...")
credit = df[CREDIT].fillna(0)
active = credit[credit > 0]
p99 = active.quantile(.99)

fig, ax = plt.subplots(figsize=(7, 5))
ax.hist(active[active <= p99], bins=60, color='steelblue', edgecolor='white', alpha=.8)
ax.axvline(active.mean(),   color='red',    ls='--', lw=2, label=f'평균 {active.mean():,.0f}')
ax.axvline(active.median(), color='orange', ls='--', lw=2, label=f'중앙값 {active.median():,.0f}')
ax.set_xlabel('크레딧 사용량 (P99 이하)')
ax.set_ylabel('유저 수')
ax.set_title('크레딧 사용 분포 (Linear Scale)')
ax.legend()
plt.tight_layout()
save('01_distribution_linear.png')

fig, ax = plt.subplots(figsize=(7, 5))
log_v = np.log10(active + 1)
ax.hist(log_v, bins=60, color='teal', edgecolor='white', alpha=.8)
ax.axvline(np.log10(active.mean()),   color='red',    ls='--', lw=2, label='평균')
ax.axvline(np.log10(active.median()), color='orange', ls='--', lw=2, label='중앙값')
ticks = [1, 2, 3, 4, 5, 6]
ax.set_xticks(ticks)
ax.set_xticklabels([f'$10^{{{t}}}$' for t in ticks])
ax.set_xlabel('log10(크레딧 사용량)')
ax.set_ylabel('유저 수')
ax.set_title('크레딧 사용 분포 (Log Scale)')
ax.legend()
plt.tight_layout()
save('01_distribution_log.png')

# 소진율
df['월_소진율'] = np.where(
    df['현재 월 크레딧 할당량'] > 0,
    (1 - df['현재 월 크레딧 잔여량'].fillna(0) / df['현재 월 크레딧 할당량']) * 100,
    np.nan
)
burn = df['월_소진율'].dropna().clip(0, 100)

fig, ax = plt.subplots(figsize=(7, 5))
ax.hist(burn, bins=50, color='coral', edgecolor='white', alpha=.8)
ax.axvline(burn.mean(),   color='red',    ls='--', lw=2, label=f'평균 {burn.mean():.1f}%')
ax.axvline(burn.median(), color='orange', ls='--', lw=2, label=f'중앙값 {burn.median():.1f}%')
ax.set_xlabel('소진율 (%)')
ax.set_ylabel('유저 수')
ax.set_title('월 크레딧 소진율 분포')
ax.legend()
plt.tight_layout()
save('01b_burn_rate_hist.png')

burn_labels = ['0~10% (거의 안 씀)', '10~50%', '50~80%', '80~100% (거의 다 씀)']
burn_bkt = pd.cut(burn, bins=[0, 10, 50, 80, 100], labels=burn_labels, include_lowest=True)
fig, ax = plt.subplots(figsize=(7, 5))
burn_bkt.value_counts().sort_index().plot(kind='bar', ax=ax,
    color='coral', edgecolor='white', alpha=.8)
ax.set_title('월 크레딧 소진율 구간별')
ax.tick_params(axis='x', rotation=35)
ax.set_ylabel('유저 수')
plt.tight_layout()
save('01b_burn_rate_bar.png')

# ═══════════════════════════════════════════════════════════
# 2. 시계열
# ═══════════════════════════════════════════════════════════
print("[2] 시계열...")
from io import StringIO

with open(f'{DATA_DIR}/usage_data_deidentified/'
          'dashboard_2026-03-01_2026-05-31_20260616_063029.csv', 'r') as f:
    lines = f.readlines()

section_idx = [i for i, l in enumerate(lines) if l.strip().startswith('[')]
section_idx.append(len(lines))

def read_section(lines, start, end):
    data = [l for l in lines[start+2:end] if l.strip() and not l.startswith('[')]
    return ''.join(data)

dau_raw   = read_section(lines, section_idx[0], section_idx[1])
model_raw = read_section(lines, section_idx[1], section_idx[2] if len(section_idx) > 2 else len(lines))

dau_df   = pd.read_csv(StringIO(dau_raw),   names=['날짜','DAU','방문자수'])
model_df = pd.read_csv(StringIO(model_raw), names=['날짜','요청수','토큰수','생성수','크레딧','TTFT','완료시간'])
dau_df['날짜']   = pd.to_datetime(dau_df['날짜'],   errors='coerce')
model_df['날짜'] = pd.to_datetime(model_df['날짜'], errors='coerce')
dau_df   = dau_df.dropna(subset=['날짜'])
model_df = model_df.dropna(subset=['날짜'])
for col in ['DAU','방문자수']:
    dau_df[col] = pd.to_numeric(dau_df[col], errors='coerce')
for col in ['요청수','토큰수','생성수','크레딧','TTFT','완료시간']:
    model_df[col] = pd.to_numeric(model_df[col], errors='coerce')

fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(dau_df['날짜'], dau_df['DAU'], color='steelblue', lw=1, alpha=.5)
ax.plot(dau_df['날짜'], dau_df['DAU'].rolling(7).mean(), color='steelblue', lw=2.5, label='7일 이동평균')
ax.fill_between(dau_df['날짜'], dau_df['DAU'], alpha=.1, color='steelblue')
ax.set_title('일별 DAU', fontsize=11)
ax.set_ylabel('유저 수')
ax.legend()
plt.tight_layout()
save('02_dau.png')

fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(dau_df['날짜'], dau_df['방문자수'], color='teal', lw=1, alpha=.5)
ax.plot(dau_df['날짜'], dau_df['방문자수'].rolling(7).mean(), color='teal', lw=2.5, label='7일 이동평균')
ax.fill_between(dau_df['날짜'], dau_df['방문자수'], alpha=.1, color='teal')
ax.set_title('일별 방문자 수', fontsize=11)
ax.set_ylabel('유저 수')
ax.legend()
plt.tight_layout()
save('02_visitors.png')

fig, ax = plt.subplots(figsize=(14, 4))
ax.bar(model_df['날짜'], model_df['크레딧'], color='coral', alpha=.45, label='일별')
ax.plot(model_df['날짜'], model_df['크레딧'].rolling(7).mean(), color='red', lw=2.5, label='7일 이동평균')
ax.set_title('일별 크레딧 소비', fontsize=11)
ax.set_ylabel('크레딧')
ax.legend()
plt.tight_layout()
save('02_credit.png')

day_names = ['월','화','수','목','금','토','일']
dau_df['요일']   = dau_df['날짜'].dt.dayofweek
model_df['요일'] = model_df['날짜'].dt.dayofweek

fig, ax = plt.subplots(figsize=(6, 4))
dau_df.groupby('요일')['DAU'].mean().rename(index=dict(enumerate(day_names))).plot(
    kind='bar', ax=ax, color='steelblue', edgecolor='white', alpha=.85)
ax.set_title('요일별 평균 DAU')
ax.tick_params(axis='x', rotation=0)
plt.tight_layout()
save('02b_weekday_dau.png')

fig, ax = plt.subplots(figsize=(6, 4))
model_df.groupby('요일')['크레딧'].mean().rename(index=dict(enumerate(day_names))).plot(
    kind='bar', ax=ax, color='coral', edgecolor='white', alpha=.85)
ax.set_title('요일별 평균 크레딧 소비')
ax.tick_params(axis='x', rotation=0)
plt.tight_layout()
save('02b_weekday_credit.png')

# ═══════════════════════════════════════════════════════════
# 3. 코호트
# ═══════════════════════════════════════════════════════════
print("[3] 코호트...")
def cohort_group(ym):
    if pd.isna(ym): return '기타'
    s = str(ym)
    if s < '2025-01': return '2025년 이전'
    if s < '2026-01': return '2025년'
    return s

df['가입월'] = df['최초 가입일'].dt.to_period('M').astype(str)
df['코호트'] = df['가입월'].apply(cohort_group)
cohort_order = [c for c in ['2025년 이전','2025년',
                             '2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','기타']
                if c in df['코호트'].unique()]

cohort_df = df.groupby('코호트')[CREDIT].agg(
    유저수='count',
    활성유저수=lambda x: (x > 0).sum(),
    평균크레딧='mean',
    중앙값크레딧='median',
    총크레딧='sum',
).reindex(cohort_order)
cohort_df['활성화율(%)'] = (cohort_df['활성유저수'] / cohort_df['유저수'] * 100).round(1)

fig, ax = plt.subplots(figsize=(8, 5))
cohort_df['활성화율(%)'].plot(kind='bar', ax=ax, color='steelblue', edgecolor='white', alpha=.85)
ax.set_title('코호트별 활성화율 (%)')
ax.tick_params(axis='x', rotation=45)
ax.set_ylabel('%')
plt.tight_layout()
save('03_cohort_activation.png')

fig, ax = plt.subplots(figsize=(8, 5))
cohort_df[['평균크레딧','중앙값크레딧']].plot(kind='bar', ax=ax,
    color=['salmon','steelblue'], edgecolor='white', alpha=.8)
ax.set_title('코호트별 크레딧 사용량')
ax.tick_params(axis='x', rotation=45)
ax.legend(['평균','중앙값'])
plt.tight_layout()
save('03_cohort_credit.png')

fig, ax = plt.subplots(figsize=(8, 5))
cohort_df['유저수'].plot(kind='bar', ax=ax, color='teal', edgecolor='white', alpha=.85)
ax.set_title('코호트별 유저 수')
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
save('03_cohort_users.png')

# ═══════════════════════════════════════════════════════════
# 4. 세그먼트
# ═══════════════════════════════════════════════════════════
print("[4] 세그먼트...")
df['신분_정제'] = df['신분'].str.split(',').str[0].str.strip()
df_m = df[df['신분_정제'].isin(['학생','교수','교직원'])].copy()

seg = df_m.groupby('신분_정제')[CREDIT].agg(
    유저수='count',
    활성유저수=lambda x: (x > 0).sum(),
    평균='mean', 중앙값='median',
    P90=lambda x: x.quantile(.9),
    최대='max', 총합='sum',
)
seg['활성화율(%)']  = (seg['활성유저수'] / seg['유저수'] * 100).round(1)
seg['총합_비중(%)'] = (seg['총합'] / seg['총합'].sum() * 100).round(1)

PAL = {'학생':'steelblue','교수':'coral','교직원':'teal'}

fig, ax = plt.subplots(figsize=(7, 5))
for 신분, grp in df_m[df_m[CREDIT] > 0].groupby('신분_정제'):
    ax.hist(np.log10(grp[CREDIT]+1), bins=40, alpha=.5, label=신분, color=PAL.get(신분,'gray'))
ax.set_xlabel('log10(크레딧 사용량)')
ax.set_ylabel('유저 수')
ax.set_title('신분별 크레딧 사용 분포 (Log Scale)')
ax.legend()
plt.tight_layout()
save('04a_identity_dist.png')

fig, ax2 = plt.subplots(figsize=(7, 5))
ids = ['학생','교수','교직원']
vals = [seg.loc[s,'중앙값'] if s in seg.index else 0 for s in ids]
ax2.bar(ids, vals, color=[PAL[s] for s in ids], edgecolor='white', alpha=.85)
ax2t = ax2.twinx()
actv = [seg.loc[s,'활성화율(%)'] if s in seg.index else 0 for s in ids]
ax2t.plot(ids, actv, 'o--', color='black', lw=2, ms=8, label='활성화율(%)')
ax2t.set_ylabel('활성화율 (%)')
ax2.set_ylabel('크레딧 중앙값')
ax2.set_title('신분별 크레딧 중앙값 & 활성화율')
ax2t.legend(loc='upper right')
plt.tight_layout()
save('04a_identity_median.png')

# 소속별
dept = df_m.groupby('소속')[CREDIT].agg(
    유저수='count',
    활성유저수=lambda x: (x > 0).sum(),
    총크레딧='sum', 중앙값크레딧='median', 평균크레딧='mean',
).sort_values('총크레딧', ascending=False)
dept['활성화율(%)'] = (dept['활성유저수'] / dept['유저수'] * 100).round(1)

top20t = dept.head(20)
fig, ax = plt.subplots(figsize=(8, 7))
ax.barh(range(len(top20t)), top20t['총크레딧'], color='steelblue', alpha=.8)
ax.set_yticks(range(len(top20t)))
ax.set_yticklabels(top20t.index, fontsize=8.5)
ax.invert_yaxis()
ax.set_xlabel('총 크레딧')
ax.set_title('소속별 총 크레딧 TOP 20')
plt.tight_layout()
save('04b_dept_total.png')

top20m = dept[dept['유저수'] >= 5].nlargest(20, '중앙값크레딧')
fig, ax = plt.subplots(figsize=(8, 7))
ax.barh(range(len(top20m)), top20m['중앙값크레딧'], color='coral', alpha=.8)
ax.set_yticks(range(len(top20m)))
ax.set_yticklabels(top20m.index, fontsize=8.5)
ax.invert_yaxis()
ax.set_xlabel('크레딧 중앙값')
ax.set_title('소속별 1인당 크레딧 중앙값 TOP 20\n(최소 5명 이상)')
plt.tight_layout()
save('04b_dept_median.png')

# 직급/과정별
students = df_m[df_m['신분_정제'] == '학생'].copy()
students['직급_정제'] = students['직급/과정'].fillna('미입력').str.strip()
top_courses = students['직급_정제'].value_counts().head(8).index

cnt = students['직급_정제'].value_counts().head(10)
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(cnt.index, cnt.values, color='steelblue', edgecolor='white', alpha=.85)
ax.set_title('학생 직급/과정별 유저 수 (상위 10)')
ax.tick_params(axis='x', rotation=40)
plt.tight_layout()
save('04c_course_count.png')

med = (students[students['직급_정제'].isin(top_courses)]
       .groupby('직급_정제')[CREDIT].median()
       .sort_values(ascending=False))
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(med.index, med.values, color='coral', edgecolor='white', alpha=.85)
ax.set_title('학생 직급/과정별 크레딧 중앙값')
ax.tick_params(axis='x', rotation=40)
ax.set_ylabel('크레딧 중앙값')
plt.tight_layout()
save('04c_course_median.png')

# Heavy user
p90 = df_m[CREDIT].quantile(.90)
df_m['tier'] = pd.cut(
    df_m[CREDIT].fillna(0),
    bins=[-1, 0, df_m[CREDIT].quantile(.5), p90, float('inf')],
    labels=['미사용','하위 50%','중간 40%','상위 10%']
)
heavy   = df_m[df_m['tier'] == '상위 10%']
all_act = df_m[df_m[CREDIT] > 0]

id_all   = all_act['신분_정제'].value_counts(normalize=True) * 100
id_heavy = heavy['신분_정제'].value_counts(normalize=True) * 100

fig, ax = plt.subplots(figsize=(7, 5))
pd.DataFrame({'전체 활성':id_all,'상위 10%':id_heavy}).fillna(0).plot(
    kind='bar', ax=ax, color=['steelblue','coral'], edgecolor='white', alpha=.85)
ax.set_title('신분 구성: 전체 활성 vs 상위 10%')
ax.tick_params(axis='x', rotation=0)
ax.set_ylabel('%')
ax.legend()
plt.tight_layout()
save('04d_heavy_identity.png')

top_dept = heavy['소속'].value_counts().head(12)
fig, ax = plt.subplots(figsize=(7, 5))
ax.barh(range(len(top_dept)), top_dept.values, color='coral', alpha=.8)
ax.set_yticks(range(len(top_dept)))
ax.set_yticklabels(top_dept.index, fontsize=8.5)
ax.invert_yaxis()
ax.set_xlabel('유저 수')
ax.set_title('상위 10% 유저의 소속 분포')
plt.tight_layout()
save('04d_heavy_dept.png')

# 미사용 유저
zero = df_m[df_m[CREDIT] == 0]
zr_id = (df_m.groupby('신분_정제')
         .apply(lambda x: (x[CREDIT]==0).sum() / len(x) * 100)
         .round(1))
fig, ax = plt.subplots(figsize=(6, 4))
zr_id.plot(kind='bar', ax=ax, color='gray', edgecolor='white', alpha=.8)
ax.set_title('신분별 미사용율 (%)')
ax.tick_params(axis='x', rotation=0)
ax.set_ylabel('%')
plt.tight_layout()
save('04e_zero_identity.png')

zr_c = (df_m.groupby('코호트')
        .apply(lambda x: (x[CREDIT]==0).sum() / len(x) * 100)
        .reindex(cohort_order).dropna().round(1))
fig, ax = plt.subplots(figsize=(6, 4))
zr_c.plot(kind='bar', ax=ax, color='gray', edgecolor='white', alpha=.8)
ax.set_title('가입 코호트별 미사용율 (%)')
ax.tick_params(axis='x', rotation=45)
ax.set_ylabel('%')
plt.tight_layout()
save('04e_zero_cohort.png')

# ═══════════════════════════════════════════════════════════
# 5. 모델 사용
# ═══════════════════════════════════════════════════════════
print("[5] 모델...")
model_stats = {}
for m in MODELS:
    mc = model_credit_sum(df, m)
    if mc.sum() > 0:
        model_stats[m] = {'총_크레딧': mc.sum(), '사용_유저수': (mc > 0).sum()}

mu = pd.DataFrame(model_stats).T.sort_values('총_크레딧', ascending=False)
mu['비중(%)'] = (mu['총_크레딧'] / mu['총_크레딧'].sum() * 100).round(2)

top15 = mu.head(15)
colors = list(plt.cm.tab20.colors[:15])

fig, ax = plt.subplots(figsize=(8, 6))
ax.barh(range(len(top15)), top15['총_크레딧'], color=colors, alpha=.85)
ax.set_yticks(range(len(top15)))
ax.set_yticklabels(top15.index, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('총 크레딧')
ax.set_title('모델별 총 크레딧 TOP 15')
plt.tight_layout()
save('05a_model_credit.png')

fig, ax = plt.subplots(figsize=(8, 6))
ax.barh(range(len(top15)), top15['사용_유저수'], color=colors, alpha=.85)
ax.set_yticks(range(len(top15)))
ax.set_yticklabels(top15.index, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('사용 유저 수')
ax.set_title('모델별 사용 유저 수 TOP 15')
plt.tight_layout()
save('05a_model_users.png')

top8 = mu.head(8).index.tolist()
by_id = {}
for 신분 in ['학생','교수','교직원']:
    sub = df_m[df_m['신분_정제'] == 신분]
    by_id[신분] = {m: model_credit_sum(sub, m).sum() for m in top8}

mi_df  = pd.DataFrame(by_id).T
mi_pct = mi_df.div(mi_df.sum(axis=1), axis=0) * 100

fig, ax = plt.subplots(figsize=(13, 5))
mi_pct.plot(kind='bar', ax=ax, colormap='tab10', edgecolor='white', alpha=.85, width=.7)
ax.set_title('신분별 모델 사용 비중 (상위 8개 모델)', fontsize=12)
ax.tick_params(axis='x', rotation=0)
ax.set_ylabel('사용 비중 (%)')
ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8)
plt.tight_layout()
save('05b_model_identity.png')

top10 = mu.head(10).index.tolist()
heavy_u = df_m[df_m['tier'] == '상위 10%']
light_u = df_m[df_m['tier'] == '하위 50%']
hm = {m: model_credit_sum(heavy_u, m).sum() for m in top10}
lm = {m: model_credit_sum(light_u, m).sum() for m in top10}
cmp = pd.DataFrame({'상위 10% (Heavy)': hm, '하위 50% (Light)': lm})
cmp_pct = cmp.div(cmp.sum(axis=0), axis=1) * 100

fig, ax = plt.subplots(figsize=(13, 5))
cmp_pct.T.plot(kind='bar', ax=ax, colormap='tab10', edgecolor='white', alpha=.85)
ax.set_title('Heavy User vs Light User 모델 선호도 비교', fontsize=12)
ax.tick_params(axis='x', rotation=0)
ax.set_ylabel('사용 비중 (%)')
ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8)
plt.tight_layout()
save('05c_model_heavy_light.png')

with open(f'{DATA_DIR}/usage_data_deidentified/'
          'usage_export_2026-03-01_to_2026-05-31_20260616_022658.csv',
          encoding='utf-8-sig') as f:
    lines_raw = [l.rstrip() for l in f if l.strip()]
header = lines_raw[0].split(',')
vals   = lines_raw[1].split(',')
feat = {}
for k, v in zip(header, vals):
    try:
        fv = float(v)
        if k != '합계' and fv > 0:
            feat[k] = fv
    except Exception:
        pass
feat_s = pd.Series(feat, dtype='float64').sort_values(ascending=False)
feat_arr = np.array(list(feat_s), dtype=np.float64)

fig, ax = plt.subplots(figsize=(9, 9))
n = len(feat_arr)
pal = (list(plt.cm.Set3.colors) * ((n // 12) + 2))[:n]
ax.pie(feat_arr, labels=feat_s.index, autopct='%1.1f%%', colors=pal, startangle=90)
ax.set_title('기능별 크레딧 비중 (2026-03 ~ 05)', fontsize=12)
plt.tight_layout()
save('05d_feature.png')

# ═══════════════════════════════════════════════════════════
# 6. 유료 전환
# ═══════════════════════════════════════════════════════════
print("[6] 유료 전환...")
df_m['유료전환'] = df_m['개인 구매 크레딧'].fillna(0) > 0
by_id_paid = df_m.groupby('신분_정제')['유료전환'].agg(유저수='count', 전환수='sum', 전환율='mean')
by_id_paid['전환율(%)'] = (by_id_paid['전환율'] * 100).round(2)

df_m['크레딧_구간'] = pd.cut(
    df_m[CREDIT].fillna(0),
    bins=[-1, 0, 100, 1_000, 10_000, float('inf')],
    labels=['0 (미사용)','1~100','100~1,000','1,000~10,000','10,000+'],
    right=False
)
by_bkt = df_m.groupby('크레딧_구간')['유료전환'].agg(유저수='count', 전환수='sum')
by_bkt['전환율(%)'] = (by_bkt['전환수'] / by_bkt['유저수'] * 100).round(2)

fig, ax = plt.subplots(figsize=(7, 5))
by_bkt['전환율(%)'].plot(kind='bar', ax=ax, color='gold', edgecolor='white', alpha=.9)
ax.set_title('크레딧 사용 구간별 유료 전환율 (%)')
ax.tick_params(axis='x', rotation=40)
ax.set_ylabel('%')
plt.tight_layout()
save('06_paid_bucket.png')

fig, ax = plt.subplots(figsize=(7, 5))
by_id_paid['전환율(%)'].plot(kind='bar', ax=ax,
    color=['steelblue','coral','teal'][:len(by_id_paid)], edgecolor='white', alpha=.85)
ax.set_title('신분별 유료 전환율 (%)')
ax.tick_params(axis='x', rotation=0)
ax.set_ylabel('%')
plt.tight_layout()
save('06_paid_identity.png')

print(f"\n✓ 완료! 이미지 {OUT}/ 에 저장됨")
