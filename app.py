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
        "history": {"^N225": 0.0, "^GSPC": 0.0},
        "prev_history": {"^N225": 0.0, "^GSPC": 0.0},
        "prev_day_close_history": {"^N225": 0.0, "^GSPC": 0.0},
        "labels": {"^N225": "日経平均株価", "^GSPC": "S&P500"},
        "stock_info": {"^N225": "Nikkei 225", "^GSPC": "S&P 500"}
    }
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
            for key in default_config:
                if key not in loaded_config:
                    loaded_config[key] = default_config[key]
            return loaded_config
    else:
        return default_config

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config = load_config()

# --- データ取得関数 ---
def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
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

# --- サイドバー：銘柄設定 ---
st.sidebar.title("⚙️ 銘柄設定")
with st.sidebar.expander("銘柄の追加・削除", expanded=True):
    new_name = st.text_input("日本語名（例：トヨタ自動車）")
    new_code = st.text_input("コード（例：7203）")
    
    if st.button("追加"):
        if new_name and new_code:
            symbol = new_code if "." in new_code else f"{new_code}.T"
            if symbol not in config["indices"] and symbol not in [s["symbol"] for s in config["stocks"]]:
                config["stocks"].append({"name": new_name, "symbol": symbol})
                config["labels"][symbol] = new_name
                config["stock_info"][symbol] = new_name
                if symbol not in config["history"]: config["history"][symbol] = 0.0
                if symbol not in config["prev_history"]: config["prev_history"][symbol] = 0.0
                if symbol not in config["prev_day_close_history"]: config["prev_day_close_history"][symbol] = 0.0
                
                save_config(config)
                st.success(f"{new_name} を追加しました")
                st.rerun()
        else:
            st.warning("名前とコードを入力してください")

    if config["stocks"]:
        st.write("---")
        del_list = []
        for i, stock in enumerate(config["stocks"]):
            col1, col2 = st.columns([3, 1])
            col1.write(f"{stock['name']} ({stock['symbol']})")
            if col2.button("削除", key=f"del_{i}"):
                del_list.append(i)
        
        if st.button("削除を実行"):
            for i in sorted(del_list, reverse=True):
                config["stocks"].pop(i)
            save_config(config)
            st.rerun()

# --- メイン画面 ---
st.title("📈 株価監視ダッシュボード")
st.write("市場が閉まっている時間は、前日の終値を表示します。")

status_placeholder = st.empty()

if st.button("🔄 更新", type="primary"):
    all_targets = config["indices"] + [s["symbol"] for s in config["stocks"]]
    success_count = 0
    fail_count = 0
    
    status_placeholder.info(f"データ取得中... (対象: {len(all_targets)}件)")
    
    for symbol in all_targets:
        current, prev_day_close = get_stock_data(symbol)
        if current is not None:
            old_price = config["history"].get(symbol, 0.0)
            if old_price != 0 and current != old_price:
                config["prev_history"][symbol] = old_price
            
            config["history"][symbol] = current
            config["prev_day_close_history"][symbol] = prev_day_close
            success_count += 1
        else:
            fail_count += 1
    
    save_config(config)
    status_placeholder.success(f"更新完了！ 成功: {success_count}, 失敗: {fail_count}")
    st.rerun()

# --- 表示処理 ---
items_to_display = []
for idx in config["indices"]:
    items_to_display.append({"name": config["labels"].get(idx, idx), "symbol": idx})
for s in config["stocks"]:
    items_to_display.append({"name": s["name"], "symbol": s["symbol"]})

for item in items_to_display:
    name = item["name"]
    symbol = item["symbol"]
    current_price = config["history"].get(symbol, 0.0)
    prev_update_price = config["prev_history"].get(symbol, 0.0)
    prev_day_close = config["prev_day_close_history"].get(symbol, 0.0)
    
    diff_amount = 0
    diff_percent = 0.0
    color = "#000000"
    display_diff = "-"
    
    if current_price != 0 and prev_update_price != 0:
        diff_amount = current_price - prev_update_price
        diff_percent = (diff_amount / prev_update_price) * 100
        
        if diff_amount > 0:
            color = "#00008B"
        elif diff_amount < 0:
            color = "#FF0000"
        else:
            color = "#888888"
            
        display_diff = f"{diff_amount:,.0f} ({diff_percent:+.2f}%)"

    # --- 修正ポイント：HTMLを最小限に絞ってサイズを制御 ---
    st.markdown(f"### {name}")
    
    # 現在株価（50px）
    col_l1, col_v1 = st.columns([1, 3])
    col_l1.markdown("**現在株価**")
    col_v1.markdown(f"<div style='font-size: 60px; font-weight: bold;'>{current_price:,}</div>", unsafe_allow_html=True)

    # 前回比（24px）
    col_l2, col_v2 = st.columns([1, 3])
    col_l2.markdown("**前回比**")
    col_v2.markdown(f"<div style='font-size: 35px; font-weight: bold; color: {color};'>{display_diff}</div>", unsafe_allow_html=True)

    # 前日終値（24px）
    col_l3, col_v3 = st.columns([1, 3])
    col_l3.markdown("**前日終値**")
    col_v3.markdown(f"<div style='font-size: 40px; font-weight: bold; color: #000;'>{prev_day_close:,}</div>", unsafe_allow_html=True)
    
    st.markdown("---")

with st.expander("詳細ログ"):
    st.write("現在の履歴:", config["history"])
    st.write("前回更新時価格:", config["prev_history"])
    st.write("前日の終値履歴:", config["prev_day_close_history"])
    st.write("銘柄リスト:", config["stocks"])
