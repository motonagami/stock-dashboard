import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

# --- 設定 ---
CONFIG_FILE = "config.json"

# --- ページ設定 ---
st.set_page_config(page_title="株価監視ダッシュボード", layout="wide")

# --- データ管理関数 ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "indices": ["^N225", "^GSPC"],
        "stocks": [],
        "history": {},
        "labels": {
            "^N225": "日経平均株価",
            "^GSPC": "S&P500"
        }
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# --- 初期化 ---
if 'config' not in st.session_state:
    st.session_state.config = load_config()

# --- データ取得関数 ---
def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return None
    except:
        return None

# --- サイドバー：銘柄管理 ---
with st.sidebar:
    st.header("⚙️ 銘柄設定")
    st.write("監視する銘柄を管理します。")
    
    all_tickers = st.session_state.config["indices"] + st.session_state.config["stocks"]
    
    if all_tickers:
        for ticker in all_tickers:
            cols = st.columns([4, 1])
            # 表示名をクレンジング（^を消す、.Tを消す）
            display_name = st.session_state.config["labels"].get(ticker, ticker.replace(".T", "").replace("^", ""))
            cols[0].write(display_name)
            if cols[1].button("削除", key=f"del_{ticker}"):
                if ticker in st.session_state.config["indices"]:
                    st.session_state.config["indices"].remove(ticker)
                else:
                    st.session_state.config["stocks"].remove(ticker)
                save_config(st.session_state.config)
                st.rerun()
    else:
        st.write("銘柄が登録されていません。")

    st.divider()
    new_ticker = st.text_input("追加する証券コード", placeholder="例: 7203.T")
    if st.button("銘柄を追加"):
        if new_ticker and new_ticker not in st.session_state.config["indices"] and new_ticker not in st.session_state.config["stocks"]:
            st.session_state.config["stocks"].append(new_ticker)
            save_config(st.session_state.config)
            st.rerun()
    
    st.caption("※証券コードの例:\nトヨタ: 7203.T\nソニー: 6758.T\nApple: AAPL")

# --- メイン画面 ---
st.title("📈 株価監視ダッシュボード")
st.write("市場が閉まっている時間は、前日の終値を表示します。")

# 目立つ更新ボタン
if st.button("🚀 最新の株価を更新", type="primary", use_container_width=True):
    with st.spinner("データを取得中..."):
        for ticker in st.session_state.config["indices"] + st.session_state.config["stocks"]:
            current_price = get_stock_data(ticker)
            if current_price:
                st.session_state.config["history"][ticker] = current_price
        save_config(st.session_state.config)
        st.rerun()

st.divider()

# --- 結果の表示 ---
if st.session_state.config["indices"] or st.session_state.config["stocks"]:
    all_items = []
    # インデックスの表示用ラベルを付与
    for ticker in st.session_state.config["indices"]:
        label = st.session_state.config["labels"].get(ticker, ticker)
        all_items.append({"name": label, "symbol": ticker})
    # 個別株の表示用ラベルを付与（.Tなどを除去）
    for ticker in st.session_state.config["stocks"]:
        label = ticker.replace(".T", "").replace("^", "")
        all_items.append({"name": label, "symbol": ticker})

    # グリッド表示
    num_items = len(all_items)
    cols_count = min(3, num_items)
    
    for i in range(0, num_items, cols_count):
        cols = st.columns(cols_count)
        for j, item in enumerate(all_items[i:i+cols_count]):
            with cols[j]:
                price = st.session_state.config["history"].get(item["symbol"])
                if price:
                    st.metric(label=item["name"], value=f"{price:,.2f}")
                else:
                    st.write(f"{item['name']}")
                    st.caption("「更新」ボタンを押してください")
else:
    st.info("サイドバーから銘柄を追加してください。")

st.divider()
st.caption("※データ取得に時間がかかる場合があります。")
