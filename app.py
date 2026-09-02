import streamlit as st
import yfinance as yf
import json
import os

# --- 設定と初期化 ---
CONFIG_FILE = "config.json"

def load_config():
    default_config = {
        "indices": ["^N225", "^GSPC"],
        "stocks": [],
        "labels": {"^N225": "日経平均株価", "^GSPC": "S&P500"},
        "stock_info": {"^N225": "Nikkei 225", "^GSPC": "S&P 500"}
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
                for key in default_config:
                    if key not in loaded_config:
                        loaded_config[key] = default_config[key]
                return loaded_config
        except Exception as e:
            st.error(f"config.json の読み込みエラー: {e}")
            return default_config
    else:
        return default_config

config = load_config()

# --- セッション状態の初期化 ---
# 当日のみの追加銘柄をメモリに保持するための変数
if "today_stocks" not in st.session_state:
    st.session_state.today_stocks = []

# --- データ取得関数 ---
def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        # 直近2日分を取得
        df = ticker.history(period="2d")
        if len(df) >= 2:
            current_price = round(df['Close'].iloc[-1], 0)
            prev_day_close = round(df['Close'].iloc[-2], 0)
            return current_price, prev_day_close
        elif len(df) == 1:
            price = round(df['Close'].iloc[-1], 0)
            return price, price
        else:
            return None, None
    except Exception:
        return None, None

# --- 画面の構成 ---
st.set_page_config(page_title="自分専用・株価監視", layout="wide")

st.title("📈 株価監視ダッシュボード")
st.write("※PCで管理アプリを使い config.json を更新することで常設銘柄が反映されます。")

# --- サイドバー：当日のみの銘柄追加 ---
st.sidebar.title("⚙️ 当日の追加")
with st.sidebar.expander("一時的な銘柄追加", expanded=True):
    new_name = st.text_input("日本語名（例：トヨタ自動車）")
    new_code = st.text_input("コード（例：7203）")
    
    if st.button("追加", type="primary"):
        if new_name and new_code:
            symbol = new_code if "." in new_code else f"{new_code}.T"
            if not any(s["symbol"] == symbol for s in config["stocks"]) and \
               not any(s["symbol"] == symbol for s in st.session_state.today_stocks):
                
                st.session_state.today_stocks.append({"name": new_name, "symbol": symbol})
                st.success(f"{new_name} を追加しました（ブラウザ更新まで保持）")
                st.rerun()
            else:
                st.warning("既にリストに含まれています。")
        else:
            st.warning("名前とコードを入力してください")

    if st.session_state.today_stocks:
        st.write("---")
        for i, stock in enumerate(st.session_state.today_stocks):
            col1, col2 = st.columns([3, 1])
            col1.write(f"{stock['name']} ({stock['symbol']})")
            if col2.button("削除", key=f"del_tmp_{i}"):
                st.session_state.today_stocks.pop(i)
                st.rerun()

# --- メイン画面：更新ボタン ---
status_placeholder = st.empty()

if st.button("🔄 株価を更新", type="primary"):
    # 常設銘柄 + 当日の追加銘柄
    all_targets = config["indices"] + [s["symbol"] for s in config["stocks"]] + \
                   [s["symbol"] for s in st.session_state.today_stocks]
    
    success_count = 0
    fail_count = 0
    
    status_placeholder.info(f"データ取得中... (対象: {len(all_targets)}件)")
    
    for symbol in all_targets:
        current, prev_day_close = get_stock_data(symbol)
        if current is not None:
            success_count += 1
        else:
            fail_count += 1
    
    status_placeholder.success(f"更新完了！ 成功: {success_count}, 失敗: {fail_count}")
    st.rerun()

# --- 表示処理 ---
# 表示対象を統合
items_to_display = []
# 1. 常設指数
for idx in config["indices"]:
    items_to_display.append({"name": config["labels"].get(idx, idx), "symbol": idx})
# 2. 常設個別銘柄
for s in config["stocks"]:
    items_to_display.append({"name": s["name"], "symbol": s["symbol"]})
# 3. 当日の追加銘柄
for s in st.session_state.today_stocks:
    items_to_display.append({"name": s["name"], "symbol": s["symbol"]})

for item in items_to_display:
    name = item["name"]
    symbol = item["symbol"]
    current_price, prev_day_close = get_stock_data(symbol)
    
    diff_amount = 0
    diff_percent = 0.0
    color = "#000000"
    display_diff = "-"
    
    if current_price is not None and prev_day_close is not None:
        diff_amount = current_price - prev_day_close
        diff_percent = (diff_amount / prev_day_close) * 100
        
        if diff_amount < 0:
            color = "#FF0000" # マイナスは赤
        elif diff_amount > 0:
            color = "#000000" # プラスは黒
        else:
            color = "#888888" # 変化なしはグレー
            
        display_diff = f"{diff_amount:,.0f} ({diff_percent:+.2f}%)"

    # 表示ブロック
    st.markdown(f"### {name}")
    
    # 現在株価
    col_l1, col_v1 = st.columns([1, 3])
    col_l1.markdown("**現在株価**")
    col_v1.markdown(f"<div style='font-size: 60px; font-weight: bold;'>{current_price if current_price else '--':,}</div>", unsafe_allow_html=True)

    # 前日比（ネットから取った「前日終値」との比較）
    col_l2, col_v2 = st.columns([1, 3])
    col_l2.markdown("**前日比**")
    col_v2.markdown(f"<div style='font-size: 35px; font-weight: bold; color: {color};'>{display_diff}</div>", unsafe_allow_html=True)

    # 前日終値
    col_l3, col_v3 = st.columns([1, 3])
    col_l3.markdown("**前日終値**")
    col_v3.markdown(f"<div style='font-size: 40px; font-weight: bold; color: #000;'>{prev_day_close if prev_day_close else '--':,}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
