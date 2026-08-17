import streamlit as st
import yfinance as yf
import json
import os

# --- 設定と初期化 ---
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "indices": ["^N225", "^GSPC"],
            "stocks": [],
            "history": {"^N225": 0.0, "^GSPC": 0.0},
            "prev_history": {"^N225": 0.0, "^GSPC": 0.0},
            "labels": {"^N225": "日経平均株価", "^GSPC": "S&P500"},
            "stock_info": {"^N225": "Nikkei 225", "^GSPC": "S&P 500"}
        }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config = load_config()

# --- データ取得関数 ---
def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1d")
        if not df.empty:
            return round(df['Close'].iloc[-1], 0)
        else:
            return None
    except Exception:
        return None

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

# 更新ボタンとステータス表示
status_placeholder = st.empty()

if st.button("🔄 更新", type="primary"):
    all_targets = config["indices"] + [s["symbol"] for s in config["stocks"]]
    success_count = 0
    fail_count = 0
    
    status_placeholder.info(f"データ取得中... (対象: {len(all_targets)}件)")
    
    for symbol in all_targets:
        new_price = get_stock_data(symbol)
        if new_price is not None:
            old_price = config["history"].get(symbol, 0.0)
            
            # 【重要】価格が「前回と異なる場合のみ」、前回の値を「過去の履歴」に移動する
            if old_price != 0 and new_price != old_price:
                config["prev_history"][symbol] = old_price
            
            # 最新の価格を履歴に保存
            config["history"][symbol] = new_price
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
    prev_price = config["prev_history"].get(symbol, 0.0)
    
    # 差分の計算
    diff_amount = 0
    diff_percent = 0.0
    color = "#000000" # デフォルト黒
    display_diff = "-" # 初回などデータがない場合
    
    if current_price != 0 and prev_price != 0:
        diff_amount = current_price - prev_price
        diff_percent = (diff_amount / prev_price) * 100
        
        if diff_amount > 0:
            color = "#00008B" # 濃い青（上昇）
        elif diff_amount < 0:
            color = "#FF0000" # 赤（下落）
        else:
            color = "#888888" # 変化なしならグレー
            
        display_diff = f"{diff_amount:,.0f} ({diff_percent:+.2f}%)"

    # HTML/CSSによるカスタム表示（スマホ向けに最適化）
    st.markdown(f"""
    <div style="
        background-color: #f0f2f6;
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 20px;
        border: 2px solid #e0e0e0;
        text-align: center;
    ">
        <p style="font-size: 22px; margin: 0; color: #555; font-weight: bold;">{name}</p>
        <p style="font-size: 50px; font-weight: bold; margin: 15px 0; color: #000;">
            {current_price:,}
        </p>
        <p style="font-size: 24px; font-weight: bold; margin: 0; color: {color};">
            {display_diff}
        </p>
        <p style="font-size: 16px; color: #888; margin-top: 5px;">({symbol})</p>
    </div>
    """, unsafe_allow_html=True)

# デバッグ用情報
with st.expander("詳細ログ"):
    st.write("現在の履歴:", config["history"])
    st.write("前回の履歴:", config["prev_history"])
    st.write("銘柄リスト:", config["stocks"])
