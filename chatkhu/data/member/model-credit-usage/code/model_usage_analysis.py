import warnings
warnings.filterwarnings('ignore')

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import koreanize_matplotlib  # noqa: F401  — 한글 폰트(NanumGothic) 자동 등록
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# seaborn set_style 이 rcParams 를 초기화하므로 반드시 그 뒤에 폰트 재지정
sns.set_style('whitegrid')
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.family'] = 'NanumGothic'
print("✓ 한글 폰트 설정 완료")

# ── 경로 설정 ────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, 'member_export_2026-03-01_to_2026-06-15.csv')
OUT = os.path.join(BASE, 'output')
os.makedirs(OUT, exist_ok=True)

def save(name):
    path = os.path.join(OUT, name)
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → {name} 저장 완료")

# ── 무료 모델 목록 (추가 시 이 리스트만 수정) ──────────────────────────────
FREE_MODELS = [
    'GPT-5 nano',
    'SAIT 3 Pro',
]

# ── 색상 ─────────────────────────────────────────────────────────────────────
COLORS = {
    '전체':   '#1B3A6B',
    '학생':   '#E87722',
    '교수':   '#5B9C2A',
    '교직원': '#7030A0',
}
PURPOSE_COLORS = {
    '채팅':   '#4878CF',
    '이미지': '#E8742A',
    '동영상': '#6ACC65',
}
FREE_COLORS = {
    '무료만': '#5B9C2A',
    '둘 다':  '#E87722',
    '유료만': '#1B3A6B',
    '미사용': '#CCCCCC',
}

# ── 신분 그룹 매핑 ────────────────────────────────────────────────────────────
신분_MAP = {
    '학생':   ['학생', '학생, 학생'],
    '교수':   ['교수'],
    '교직원': ['교직원', '정보처운영지원', '법인사용자'],
}
GROUPS = ['전체', '학생', '교수', '교직원']

# ── 데이터 로드 ───────────────────────────────────────────────────────────────
print("데이터 로드 중...")
df_raw = pd.read_csv(DATA_PATH, low_memory=False)

# 신분 정규화
def normalize_신분(val):
    if pd.isna(val):
        return None
    for grp, vals in 신분_MAP.items():
        if val in vals:
            return grp
    return None

df_raw['신분_grp'] = df_raw['신분'].apply(normalize_신분)
df = df_raw[df_raw['신분_grp'].notna()].copy()
print(f"  분석 대상: {len(df):,}명 (전체 {len(df_raw):,}명 중 신분 불명 {len(df_raw)-len(df)}명 제외)")

def get_df(grp):
    if grp == '전체':
        return df
    return df[df['신분_grp'] == grp]

# ── 모델 목록 추출 ────────────────────────────────────────────────────────────
chat_models, img_models, vid_models = [], [], []
seen = set()
for c in df.columns:
    if c.endswith(' Input 크레딧'):
        m = c[:-len(' Input 크레딧')]
        if m not in seen and not m.startswith('None'):
            seen.add(m); chat_models.append(m)
seen = set()
for c in df.columns:
    if c.endswith(' Image 크레딧'):
        m = c[:-len(' Image 크레딧')]
        if m not in seen:
            seen.add(m); img_models.append(m)
seen = set()
for c in df.columns:
    if c.endswith(' Video 크레딧'):
        m = c[:-len(' Video 크레딧')]
        if m not in seen:
            seen.add(m); vid_models.append(m)

all_models = chat_models + img_models + vid_models
print(f"  채팅 {len(chat_models)}개 / 이미지 {len(img_models)}개 / 동영상 {len(vid_models)}개 모델")

# ── 크레딧 합산 헬퍼 ─────────────────────────────────────────────────────────
def chat_credit(d, m):
    cols = [c for c in [f'{m} Input 크레딧', f'{m} Output 크레딧', f'{m} 웹검색 크레딧'] if c in d.columns]
    return d[cols].fillna(0).sum(axis=1)

def img_credit(d, m):
    c = f'{m} Image 크레딧'
    return d[c].fillna(0) if c in d.columns else pd.Series(0, index=d.index)

def vid_credit(d, m):
    c = f'{m} Video 크레딧'
    return d[c].fillna(0) if c in d.columns else pd.Series(0, index=d.index)

def model_credit(d, m):
    if m in chat_models:
        return chat_credit(d, m)
    elif m in img_models:
        return img_credit(d, m)
    else:
        return vid_credit(d, m)

def model_token(d, m):
    cols = [c for c in [f'{m} 입력 토큰 사용량', f'{m} 출력 토큰 사용량'] if c in d.columns]
    return d[cols].fillna(0).sum(axis=1) if cols else pd.Series(0, index=d.index)

def used_count(d, m):
    return int((model_credit(d, m) > 0).sum())

# ── 공급사 분류 ────────────────────────────────────────────────────────────────
def get_provider(m):
    if m.startswith('GPT') or m.startswith('ChatGPT') or m.startswith('Sora') or m.startswith('o1') or m.startswith('o3'):
        return 'GPT (OpenAI)'
    if m.startswith('Claude'):
        return 'Claude (Anthropic)'
    if m.startswith('Gemini') or m.startswith('Gemma') or m.startswith('Imagen') or m.startswith('Veo') or m.startswith('google/'):
        return 'Gemini (Google)'
    if m.startswith('Grok'):
        return 'Grok (xAI)'
    if m in ['SAIT 3 Pro', 'Solar Pro 3', 'Solar Pro 2', 'K-EXAONE']:
        return '국산 모델'
    if m.startswith('Llama') or m.startswith('Sonar'):
        return '기타 (Llama/Sonar 등)'
    if m == 'Super Agent':
        return 'Super Agent'
    return '기타 (이미지/동영상)'

# ── 사전 집계: 모델별 크레딧·사용자 수 ─────────────────────────────────────
print("집계 중...")

def agg_models(d, mlist, kind='credit'):
    result = {}
    for m in mlist:
        if kind == 'credit':
            result[m] = model_credit(d, m).sum()
        else:
            result[m] = used_count(d, m)
    return pd.Series(result).sort_values(ascending=False)

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 1: 모델별 총 크레딧 사용량 Top 15 (채팅 모델)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/7] 모델별 크레딧 사용량 Top 15...")
TOP_N = 15

fig, axes = plt.subplots(1, 4, figsize=(22, 7))
fig.suptitle('모델별 총 크레딧 사용량 Top 15  (채팅 모델, 2026-03-01 ~ 2026-06-15)',
             fontsize=14, fontweight='bold', y=1.01)

for ax, grp in zip(axes, GROUPS):
    d = get_df(grp)
    ser = agg_models(d, chat_models, 'credit').head(TOP_N)
    color = COLORS[grp]
    bars = ax.barh(ser.index[::-1], ser.values[::-1], color=color, alpha=0.85, edgecolor='white')
    # 막대 끝에 값 표시
    for bar, val in zip(bars, ser.values[::-1]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                f'{val:,.0f}', va='center', ha='left', fontsize=7.5)
    ax.set_title(grp, fontsize=12, fontweight='bold', color=color)
    ax.set_xlabel('크레딧', fontsize=9)
    ax.tick_params(axis='y', labelsize=8)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.margins(x=0.18)

plt.tight_layout()
save('01_top_models_by_credit.png')

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 2: 모델별 사용자 수 Top 15 (전 모델)
# ═══════════════════════════════════════════════════════════════════════════════
print("[2/7] 모델별 사용자 수 Top 15...")

fig, axes = plt.subplots(1, 4, figsize=(22, 7))
fig.suptitle('모델별 사용자 수 Top 15  (채팅+이미지+동영상, 2026-03-01 ~ 2026-06-15)',
             fontsize=14, fontweight='bold', y=1.01)

for ax, grp in zip(axes, GROUPS):
    d = get_df(grp)
    ser = agg_models(d, all_models, 'users').head(TOP_N)
    color = COLORS[grp]
    bars = ax.barh(ser.index[::-1], ser.values[::-1], color=color, alpha=0.85, edgecolor='white')
    for bar, val in zip(bars, ser.values[::-1]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                f'{int(val):,}', va='center', ha='left', fontsize=7.5)
    ax.set_title(grp, fontsize=12, fontweight='bold', color=color)
    ax.set_xlabel('사용자 수 (명)', fontsize=9)
    ax.tick_params(axis='y', labelsize=8)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.margins(x=0.18)

plt.tight_layout()
save('02_top_models_by_users.png')

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 3: 공급사별 크레딧 및 사용자 분포
# ═══════════════════════════════════════════════════════════════════════════════
print("[3/7] 공급사별 분포...")

providers = ['GPT (OpenAI)', 'Claude (Anthropic)', 'Gemini (Google)',
             'Grok (xAI)', '국산 모델', 'Super Agent', '기타 (이미지/동영상)', '기타 (Llama/Sonar 등)']
provider_order = providers

# 집계
def agg_provider(d):
    cred = {p: 0.0 for p in providers}
    users = {p: set() for p in providers}
    for m in all_models:
        p = get_provider(m)
        if p not in cred:
            continue
        cr = model_credit(d, m)
        cred[p] += cr.sum()
        users[p].update(d.index[cr > 0].tolist())
    return (pd.Series({p: cred[p] for p in providers}),
            pd.Series({p: len(users[p]) for p in providers}))

cred_data, user_data = {}, {}
for grp in GROUPS[1:]:  # 학생/교수/교직원
    c, u = agg_provider(get_df(grp))
    cred_data[grp] = c
    user_data[grp] = u

# 전체 크레딧 기준 정렬
total_cred, _ = agg_provider(df)
order = total_cred.sort_values(ascending=False).index.tolist()

fig, axes = plt.subplots(2, 1, figsize=(14, 10))
fig.suptitle('모델 공급사별 크레딧 사용량 및 사용자 수  (2026-03-01 ~ 2026-06-15)',
             fontsize=14, fontweight='bold')

x = np.arange(len(order))
width = 0.25
grp_list = ['학생', '교수', '교직원']

for ax, data_dict, ylabel in zip(axes,
                                  [cred_data, user_data],
                                  ['크레딧', '사용자 수 (명)']):
    for i, grp in enumerate(grp_list):
        vals = [data_dict[grp][p] for p in order]
        bars = ax.bar(x + i * width, vals, width, label=grp,
                      color=COLORS[grp], alpha=0.85, edgecolor='white')
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
                        f'{int(val):,}', ha='center', va='bottom', fontsize=7, rotation=45)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_xticks(x + width)
    ax.set_xticklabels(order, rotation=20, ha='right', fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.legend(fontsize=9)

plt.tight_layout()
save('03_provider_breakdown.png')

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 4: 목적별 사용 분포 (채팅 / 이미지 / 동영상)
# ═══════════════════════════════════════════════════════════════════════════════
print("[4/7] 목적별 분포...")

def purpose_stats(d):
    chat_c = sum(chat_credit(d, m).sum() for m in chat_models)
    img_c  = sum(img_credit(d, m).sum() for m in img_models)
    vid_c  = sum(vid_credit(d, m).sum() for m in vid_models)
    chat_u = len(set().union(*[set(d.index[chat_credit(d, m) > 0]) for m in chat_models]))
    img_u  = len(set().union(*[set(d.index[img_credit(d, m) > 0]) for m in img_models]))
    vid_u  = len(set().union(*[set(d.index[vid_credit(d, m) > 0]) for m in vid_models]))
    return {'채팅': (chat_c, chat_u), '이미지': (img_c, img_u), '동영상': (vid_c, vid_u)}

purpose_all = purpose_stats(df)
purpose_by_grp = {g: purpose_stats(get_df(g)) for g in GROUPS[1:]}

fig = plt.figure(figsize=(18, 8))
fig.suptitle('목적별 사용 분포: 채팅 / 이미지 / 동영상  (2026-03-01 ~ 2026-06-15)',
             fontsize=14, fontweight='bold')

# 전체 파이차트 (크레딧)
ax1 = fig.add_subplot(1, 3, 1)
pie_vals = [purpose_all[p][0] for p in ['채팅', '이미지', '동영상']]
pie_colors = [PURPOSE_COLORS[p] for p in ['채팅', '이미지', '동영상']]
wedges, texts, autotexts = ax1.pie(
    pie_vals, labels=['채팅', '이미지', '동영상'],
    colors=pie_colors, autopct='%1.1f%%', startangle=90,
    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
for t in autotexts: t.set_fontsize(10)
ax1.set_title('전체 크레딧 비율', fontsize=11, fontweight='bold')

# 신분별 크레딧 비교 막대
ax2 = fig.add_subplot(1, 3, 2)
purposes = ['채팅', '이미지', '동영상']
x = np.arange(len(purposes))
width = 0.22
for i, grp in enumerate(GROUPS[1:]):
    vals = [purpose_by_grp[grp][p][0] for p in purposes]
    ax2.bar(x + i * width, vals, width, label=grp, color=COLORS[grp], alpha=0.85, edgecolor='white')
ax2.set_ylabel('크레딧', fontsize=10)
ax2.set_xticks(x + width)
ax2.set_xticklabels(purposes, fontsize=10)
ax2.set_title('신분별 크레딧 사용량', fontsize=11, fontweight='bold')
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax2.legend(fontsize=9)

# 신분별 사용자 수 막대
ax3 = fig.add_subplot(1, 3, 3)
for i, grp in enumerate(GROUPS[1:]):
    vals = [purpose_by_grp[grp][p][1] for p in purposes]
    ax3.bar(x + i * width, vals, width, label=grp, color=COLORS[grp], alpha=0.85, edgecolor='white')
ax3.set_ylabel('사용자 수 (명)', fontsize=10)
ax3.set_xticks(x + width)
ax3.set_xticklabels(purposes, fontsize=10)
ax3.set_title('신분별 사용자 수', fontsize=11, fontweight='bold')
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax3.legend(fontsize=9)

plt.tight_layout()
save('04_purpose_breakdown.png')

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 5: 무료 vs 유료 모델 사용 비교
# ═══════════════════════════════════════════════════════════════════════════════
print("[5/7] 무료 vs 유료 모델...")

# 무료/유료 모델 사용 판별 (채팅 기준)
paid_chat = [m for m in chat_models if m not in FREE_MODELS]
free_chat = [m for m in chat_models if m in FREE_MODELS]

def free_paid_user_segments(d):
    free_mask  = pd.Series(False, index=d.index)
    paid_mask  = pd.Series(False, index=d.index)
    for m in free_chat:
        free_mask |= (chat_credit(d, m) > 0) | (model_token(d, m) > 0)
    for m in paid_chat:
        paid_mask |= (chat_credit(d, m) > 0)
    both      = (free_mask & paid_mask).sum()
    free_only = (free_mask & ~paid_mask).sum()
    paid_only = (~free_mask & paid_mask).sum()
    none_     = (~free_mask & ~paid_mask).sum()
    return {'무료만': free_only, '둘 다': both, '유료만': paid_only, '미사용': none_}

def free_paid_tokens(d):
    free_tok = sum(model_token(d, m).sum() for m in free_chat)
    paid_tok = sum(model_token(d, m).sum() for m in paid_chat)
    return free_tok, paid_tok

seg_data = {g: free_paid_user_segments(get_df(g)) for g in GROUPS}
tok_data = {g: free_paid_tokens(get_df(g)) for g in GROUPS}

fig, axes = plt.subplots(2, 1, figsize=(13, 10))
fig.suptitle(f'무료 vs 유료 모델 사용 비교  (무료 채팅 모델: {", ".join(FREE_MODELS)})',
             fontsize=13, fontweight='bold')

# 상단: 사용자 구성 (100% 스택 막대)
ax = axes[0]
bottom = np.zeros(len(GROUPS))
seg_keys = ['무료만', '둘 다', '유료만', '미사용']
for key in seg_keys:
    vals = np.array([seg_data[g][key] for g in GROUPS], dtype=float)
    totals = np.array([sum(seg_data[g].values()) for g in GROUPS], dtype=float)
    pcts = vals / totals * 100
    bars = ax.bar(GROUPS, pcts, bottom=bottom, label=key,
                  color=FREE_COLORS[key], alpha=0.88, edgecolor='white')
    for bar, pct, cnt in zip(bars, pcts, vals):
        if pct > 3:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f'{pct:.1f}%\n({int(cnt):,}명)', ha='center', va='center', fontsize=8.5)
    bottom += pcts
ax.set_ylim(0, 100)
ax.set_ylabel('사용자 비율 (%)', fontsize=10)
ax.set_title('신분별 무료/유료 모델 사용자 구성', fontsize=11, fontweight='bold')
ax.legend(loc='upper right', fontsize=9, ncol=2)

# 하단: 토큰 사용량 비율 (100% 스택 막대)
ax = axes[1]
free_pcts, paid_pcts = [], []
for g in GROUPS:
    ft, pt = tok_data[g]
    total = ft + pt
    free_pcts.append(ft / total * 100 if total > 0 else 0)
    paid_pcts.append(pt / total * 100 if total > 0 else 0)

bars1 = ax.bar(GROUPS, free_pcts, label='무료 모델', color=FREE_COLORS['무료만'], alpha=0.88, edgecolor='white')
bars2 = ax.bar(GROUPS, paid_pcts, bottom=free_pcts, label='유료 모델', color=FREE_COLORS['유료만'], alpha=0.88, edgecolor='white')
for bar, pct in zip(bars1, free_pcts):
    if pct > 3:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                f'{pct:.1f}%', ha='center', va='center', fontsize=9, color='white', fontweight='bold')
for bar, pct in zip(bars2, paid_pcts):
    if pct > 3:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                f'{pct:.1f}%', ha='center', va='center', fontsize=9, color='white', fontweight='bold')
ax.set_ylim(0, 100)
ax.set_ylabel('토큰 사용량 비율 (%)', fontsize=10)
ax.set_title('신분별 무료/유료 모델 토큰 사용량 비율 (채팅 기준)', fontsize=11, fontweight='bold')
ax.legend(fontsize=9)

plt.tight_layout()
save('05_free_vs_paid.png')

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 6: 신분별 모델 사용률 히트맵 (Top 20 채팅 모델)
# ═══════════════════════════════════════════════════════════════════════════════
print("[6/7] 모델 선호도 히트맵...")

# 전체 크레딧 기준 Top 20 채팅 모델
top20 = agg_models(df, chat_models, 'credit').head(20).index.tolist()

heatmap_data = {}
grp_sizes = {g: len(get_df(g)) for g in GROUPS[1:]}
for grp in GROUPS[1:]:
    d = get_df(grp)
    heatmap_data[grp] = {m: used_count(d, m) / grp_sizes[grp] * 100 for m in top20}

hm_df = pd.DataFrame(heatmap_data, index=top20)  # 모델×신분

fig, ax = plt.subplots(figsize=(9, 11))
sns.heatmap(hm_df, annot=True, fmt='.1f', cmap='YlOrRd',
            linewidths=0.4, linecolor='white', ax=ax,
            cbar_kws={'label': '사용률 (%)', 'shrink': 0.6})
ax.set_title('신분별 채팅 모델 사용률 히트맵  (Top 20, 각 신분 내 사용자 비율 %)',
             fontsize=12, fontweight='bold', pad=12)
ax.set_xlabel('신분', fontsize=10)
ax.set_ylabel('모델', fontsize=10)
ax.tick_params(axis='y', labelsize=8.5)
ax.tick_params(axis='x', labelsize=10)
plt.tight_layout()
save('06_model_preference_heatmap.png')

# ═══════════════════════════════════════════════════════════════════════════════
# Chart 7: 사용자당 이용 모델 수 분포 (모델 다양성)
# ═══════════════════════════════════════════════════════════════════════════════
print("[7/7] 모델 다양성 분포...")

def count_used_models(d):
    counts = pd.Series(0, index=d.index)
    for m in all_models:
        counts += (model_credit(d, m) > 0).astype(int)
    return counts

fig, ax = plt.subplots(figsize=(12, 6))
fig.suptitle('사용자당 이용 모델 수 분포 (모델 다양성)  (2026-03-01 ~ 2026-06-15)',
             fontsize=14, fontweight='bold')

max_models = 0
for grp in ['학생', '교수', '교직원']:
    d = get_df(grp)
    mc = count_used_models(d)
    max_models = max(max_models, int(mc.max()))
    mean_val = mc.mean()
    ax.hist(mc, bins=range(0, int(mc.max()) + 2), alpha=0.55, color=COLORS[grp],
            label=f'{grp} (평균 {mean_val:.1f}개)', edgecolor='white', density=False)
    ax.axvline(mean_val, color=COLORS[grp], linestyle='--', linewidth=1.8, alpha=0.9)

ax.set_xlabel('사용한 모델 수', fontsize=11)
ax.set_ylabel('사용자 수 (명)', fontsize=11)
ax.legend(fontsize=10)
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))

plt.tight_layout()
save('07_model_diversity.png')

print("\n✅ 완료! output/ 디렉토리에 7개 차트 저장됨")
