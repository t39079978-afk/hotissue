import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import platform

# =========================
# 기본 설정
# =========================
st.set_page_config(
 page_title="검색량 유행 민감도 분석",
 layout="wide"
)

# =========================
# 한글 폰트 설정
# =========================
def set_korean_font():
 system_name = platform.system()
 if system_name == "Windows":
  plt.rcParams["font.family"] = "Malgun Gothic"
 elif system_name == "Darwin":
  plt.rcParams["font.family"] = "AppleGothic"
 else:
  plt.rcParams["font.family"] = "NanumGothic"
 plt.rcParams["axes.unicode_minus"] = False

set_korean_font()

# =========================
# 그래프용 한글 -> 영어 변환
# =========================
def to_english_label(text):
 mapping = {
  "여성": "Female",
  "남성": "Male",
  "10,20대": "Age 10-20",
  "30,40대": "Age 30-40",
  "50,60대": "Age 50-60",
  "집단": "Group",
  "날짜": "Date",
  "검색량": "Search Volume",
  "유행 민감도 점수": "Trend Sensitivity Score",
  "평균 검색량": "Average Search Volume",
  "최고점 검색량": "Peak Search Volume",
  "연령대별 분석": "Age Group Analysis",
  "성별 분석": "Gender Analysis",
  "집단별 분석": "Group Analysis",
  "검색량 추이": "Search Trend",
  "집단별 최고점 검색량": "Peak Search Volume by Group"
 }
 return mapping.get(str(text), str(text))

# =========================
# 제목
# =========================
st.title("검색량 유행 민감도 분석")
st.caption("엑셀 검색량 데이터를 기반으로 집단별 유행 민감도, 유행 속도, 평균 검색량, 최고점을 분석합니다.")

# =========================
# 파일 업로드
# =========================
uploaded_files = st.file_uploader(
 "엑셀 파일을 업로드하세요. 여러 개 업로드할 수 있습니다.",
 type=["xlsx", "xls"],
 accept_multiple_files=True
)

# =========================
# 엑셀 데이터 읽기
# =========================
def read_search_sheet(file, sheet_name):
 raw_df = pd.read_excel(
  file,
  sheet_name=sheet_name,
  header=None
 )

 if raw_df.shape[0] < 4:
  st.error(f"'{sheet_name}' 시트의 행 개수가 부족합니다.")
  return pd.DataFrame()

 # 3행을 컬럼명으로 사용
 columns = raw_df.iloc[2].tolist()
 clean_columns = []

 for idx, col in enumerate(columns):
  if pd.isna(col):
   clean_columns.append(f"Unnamed_{idx}")
  else:
   clean_columns.append(str(col).strip())

 # 4행부터 실제 데이터
 df = raw_df.iloc[3:].copy()
 df.columns = clean_columns

 # 빈 행/열 제거
 df = df.dropna(axis=0, how="all")
 df = df.dropna(axis=1, how="all")

 if "날짜" not in df.columns:
  st.error(f"'{sheet_name}' 시트에서 '날짜' 컬럼을 찾을 수 없습니다.")
  st.write("현재 인식된 컬럼:", df.columns.tolist())
  return pd.DataFrame()

 # 날짜 변환
 df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
 df = df.dropna(subset=["날짜"])

 # 날짜순 정렬
 df = df.sort_values("날짜").reset_index(drop=True)

 # 숫자 변환
 for col in df.columns:
  if col != "날짜":
   df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

 return df

# =========================
# 집단 컬럼 순서 고정
# =========================
def get_group_columns(df):
 columns = list(df.columns)

 age_order = ["10,20대", "30,40대", "50,60대"]
 gender_order = ["여성", "남성"]

 if all(col in columns for col in age_order):
  return age_order

 if all(col in columns for col in gender_order):
  return gender_order

 exclude_cols = ["날짜", "전체"]
 group_cols = [
  col for col in columns
  if col not in exclude_cols
  and not str(col).startswith("Unnamed_")
 ]

 return group_cols

# =========================
# 분석 유형
# =========================
def detect_analysis_type(df):
 columns = list(df.columns)

 if all(col in columns for col in ["10,20대", "30,40대", "50,60대"]):
  return "연령대별 분석"

 if all(col in columns for col in ["여성", "남성"]):
  return "성별 분석"

 return "집단별 분석"

# =========================
# min-max 정규화
# =========================
def minmax_normalize(series):
 min_value = series.min()
 max_value = series.max()

 if max_value == min_value:
  return pd.Series([0] * len(series), index=series.index)

 return (series - min_value) / (max_value - min_value)

# =========================
# 유행 분석 계산
# =========================
def calculate_trend_analysis(df, group_cols):
 rows = []

 for group in group_cols:
  values = df[group].fillna(0)
  mean_value = values.mean()
  std_value = values.std()
  avg_abs_daily_change = values.diff().abs().mean()
  max_idx = values.idxmax()
  peak_date = df.loc[max_idx, "날짜"]
  peak_value = values.loc[max_idx]

  rows.append({
   "집단": group,
   "평균 검색량": mean_value,
   "표준편차": std_value,
   "일별 변화량 절댓값 평균": avg_abs_daily_change,
   "최고점 날짜": peak_date,
   "최고점 검색량": peak_value
  })

 result_df = pd.DataFrame(rows)

 if result_df.empty:
  return result_df

 # 유행 민감도 점수 =
 # 표준편차 정규화 + 일별 변화량 절댓값 평균 정규화
 result_df["표준편차 정규화"] = minmax_normalize(result_df["표준편차"])
 result_df["일별 변화량 정규화"] = minmax_normalize(result_df["일별 변화량 절댓값 평균"])
 result_df["유행 민감도 점수"] = (
  result_df["표준편차 정규화"] +
  result_df["일별 변화량 정규화"]
 )

 return result_df

# =========================
# 분석 결과 문장 출력
# =========================
def show_trend_summary(item_name, result_df):
 if result_df.empty:
  return

 most_sensitive = result_df.loc[result_df["유행 민감도 점수"].idxmax()]
 fastest = result_df.loc[result_df["최고점 날짜"].idxmin()]
 slowest = result_df.loc[result_df["최고점 날짜"].idxmax()]
 highest_mean = result_df.loc[result_df["평균 검색량"].idxmax()]
 lowest_mean = result_df.loc[result_df["평균 검색량"].idxmin()]

 st.subheader("분석 결과")
 st.write(f"선택한 항목은 **{item_name}**입니다.")
 st.write("")
 st.write(
  f"유행 변화에 가장 민감한 집단은 **{most_sensitive['집단']}**입니다."
 )
 st.write(
  "이는 표준편차와 일별 변화량 절댓값 평균을 정규화하여 합산한 "
  "유행 민감도 점수가 가장 높기 때문입니다."
 )
 st.write("")
 st.write(
  f"유행이 가장 빠른 집단은 **{fastest['집단']}**입니다."
 )
 st.write(
  f"유행이 가장 느린 집단은 **{slowest['집단']}**입니다."
 )
 st.write("")
 st.write(
  f"평균 검색량이 가장 높은 집단은 **{highest_mean['집단']}**입니다."
 )
 st.write(
  f"평균 검색량이 가장 낮은 집단은 **{lowest_mean['집단']}**입니다."
 )
 st.write("")
 st.write("집단별 최고점은 다음과 같습니다.")

 for _, row in result_df.iterrows():
  peak_date_text = row["최고점 날짜"].strftime("%Y-%m-%d")
  peak_value_text = f"{row['최고점 검색량']:.5f}"
  st.write(
   f"- {row['집단']}: {peak_date_text}, 검색량 {peak_value_text}"
  )

# =========================
# 시계열 그래프
# =========================
def plot_timeseries(df, group_cols, title):
 fig, ax = plt.subplots(figsize=(13, 5))

 for group in group_cols:
  ax.plot(
   df["날짜"],
   df[group],
   marker="o",
   markersize=2,
   linewidth=1.5,
   label=to_english_label(group)
  )

 ax.set_title(title)
 ax.set_xlabel("Date")
 ax.set_ylabel("Search Volume")
 ax.legend()
 ax.grid(alpha=0.25)
 plt.tight_layout()
 st.pyplot(fig)

# =========================
# 유행 민감도 그래프
# =========================
def plot_sensitivity_score(result_df, title):
 fig, ax = plt.subplots(figsize=(10, 5))

 max_group = result_df.loc[
  result_df["유행 민감도 점수"].idxmax(),
  "집단"
 ]

 colors = [
  "#F28E2B" if group == max_group else "#A0CBE8"
  for group in result_df["집단"]
 ]

 bars = ax.bar(
  [to_english_label(x) for x in result_df["집단"]],
  result_df["유행 민감도 점수"],
  color=colors
 )

 ax.set_title(title)
 ax.set_xlabel("Group")
 ax.set_ylabel("Trend Sensitivity Score")
 ax.grid(axis="y", alpha=0.25)

 for bar in bars:
  height = bar.get_height()
  ax.text(
   bar.get_x() + bar.get_width() / 2,
   height,
   f"{height:.3f}",
   ha="center",
   va="bottom",
   fontsize=10
  )

 plt.tight_layout()
 st.pyplot(fig)

# =========================
# 평균 검색량 그래프
# =========================
def plot_mean_search(result_df, title):
 fig, ax = plt.subplots(figsize=(10, 5))

 bars = ax.bar(
  [to_english_label(x) for x in result_df["집단"]],
  result_df["평균 검색량"],
  color="#59A14F"
 )

 ax.set_title(title)
 ax.set_xlabel("Group")
 ax.set_ylabel("Average Search Volume")
 ax.grid(axis="y", alpha=0.25)

 for bar in bars:
  height = bar.get_height()
  ax.text(
   bar.get_x() + bar.get_width() / 2,
   height,
   f"{height:.5f}",
   ha="center",
   va="bottom",
   fontsize=10
  )

 plt.tight_layout()
 st.pyplot(fig)

# =========================
# 최고점 검색량 그래프
# =========================
def plot_peak_search(result_df, title):
 fig, ax = plt.subplots(figsize=(10, 5))

 bars = ax.bar(
  [to_english_label(x) for x in result_df["집단"]],
  result_df["최고점 검색량"],
  color="#4C78A8"
 )

 ax.set_title(title)
 ax.set_xlabel("Group")
 ax.set_ylabel("Peak Search Volume")
 ax.grid(axis="y", alpha=0.25)

 for bar in bars:
  height = bar.get_height()
  ax.text(
   bar.get_x() + bar.get_width() / 2,
   height,
   f"{height:.5f}",
   ha="center",
   va="bottom",
   fontsize=10
  )

 plt.tight_layout()
 st.pyplot(fig)

# =========================
# 메인 실행부
# =========================
if uploaded_files:
 st.sidebar.header("분석 설정")

 file_names = [file.name for file in uploaded_files]
 selected_file_name = st.sidebar.selectbox(
  "분석할 파일을 선택하세요",
  file_names
 )

 selected_file = None
 for file in uploaded_files:
  if file.name == selected_file_name:
   selected_file = file
   break

 if selected_file is not None:
  # 절대 캐시 사용하지 않음
  xls = pd.ExcelFile(selected_file)
  sheet_names = xls.sheet_names

  selected_sheet = st.sidebar.selectbox(
   "분석할 항목을 선택하세요",
   sheet_names
  )

  df = read_search_sheet(selected_file, selected_sheet)

  if not df.empty:
   analysis_type = detect_analysis_type(df)
   group_cols = get_group_columns(df)

   st.subheader("선택 정보")
   st.write(f"선택한 파일: **{selected_file_name}**")
   st.write(f"선택한 항목: **{selected_sheet}**")
   st.write(f"분석 유형: **{analysis_type}**")

   if len(group_cols) == 0:
    st.error("비교할 집단 컬럼을 찾을 수 없습니다.")
   else:
    selected_groups = st.sidebar.multiselect(
     "분석할 집단을 선택하세요",
     group_cols,
     default=group_cols
    )

    if len(selected_groups) == 0:
     st.warning("최소 1개 이상의 집단을 선택하세요.")
    else:
     # 선택해도 원래 순서 유지
     selected_groups = [
      group for group in group_cols
      if group in selected_groups
     ]

     result_df = calculate_trend_analysis(
      df,
      selected_groups
     )

     # 네가 원한 문장형 결과
     show_trend_summary(
      selected_sheet,
      result_df
     )

     st.subheader("상세 분석표")
     display_df = result_df.copy()
     display_df["최고점 날짜"] = display_df["최고점 날짜"].dt.strftime("%Y-%m-%d")

     st.dataframe(
      display_df[[
       "집단",
       "평균 검색량",
       "표준편차",
       "일별 변화량 절댓값 평균",
       "유행 민감도 점수",
       "최고점 날짜",
       "최고점 검색량"
      ]].style.format({
       "평균 검색량": "{:.5f}",
       "표준편차": "{:.5f}",
       "일별 변화량 절댓값 평균": "{:.5f}",
       "유행 민감도 점수": "{:.3f}",
       "최고점 검색량": "{:.5f}"
      }),
      use_container_width=True
     )

     st.subheader("검색량 추이 그래프")
     plot_timeseries(
      df,
      selected_groups,
      f"{selected_sheet} {to_english_label(analysis_type)} Search Trend"
     )

     col1, col2 = st.columns(2)

     with col1:
      st.subheader("유행 민감도 점수")
      plot_sensitivity_score(
       result_df,
       f"{selected_sheet} Trend Sensitivity Score"
      )

     with col2:
      st.subheader("평균 검색량")
      plot_mean_search(
       result_df,
       f"{selected_sheet} Average Search Volume"
      )

     st.subheader("최고점 검색량")
     plot_peak_search(
      result_df,
      f"{selected_sheet} Peak Search Volume by Group"
     )

else:
 st.info("분석할 엑셀 파일을 업로드하세요.")