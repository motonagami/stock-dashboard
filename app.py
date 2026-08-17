import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime

# --- 設定 ---
CONFIG_FILE = "config.json"

# --- ページ設定 ---
st.set_page_config(page_title="株価監視ダッシュボード", layout="wide")

# --- データ管理関数 ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "labels" not in config:
                    config["labels"] = {"^N225": "日経平均株価", "^GSPC": "S&P500"}
                return config
        except:
            pass
    return {
        "indices": ["^N225", "^GSPC"],
        "stocks": [],
        "history": {}, # {ticker: {"price": 0.0, "prev_price": 0.0}}
        "labels": {"^N225": "日経平均株価", "^GSPC": "S&P500"},
        "stock_info": {} # {ticker: "会社名"}
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
        search_symbol = ticker_symbol
        if "." not in ticker_symbol and not ticker_symbol.startswith("^"):
            search_symbol = f"{ticker_symbol}.T"
        
        ticker = yf.Ticker(search_symbol)
        data = ticker.history(period="1d")
        
        if not data.empty:
            price = data['Close'].iloc[-1]
            try:
                name = ticker.info.get('longName', ticker_symbol)
                return price, name
            except:
                return price, ticker_symbol
        return None, None
    except:
        return None, None

# --- サイドバー ---
with st.sidebar:
    st.header("⚙️ 銘柄設定")
    st.write("監視する銘柄を管理します。")
    
    all_tickers = st.session_state.config["indices"] + st.session_state.config["stocks"]
    
    if all_tickers:
        for ticker in all_tickers:
            cols = st.columns([4, 1])
            # 表示名の決定ルール
            if ticker in st.session_state.config["indices"]:
                display_name = st.session_state.config["labels"].get(ticker, ticker)
            else:
                display_name = st.session_state.config["stock_info"].get(ticker, ticker.replace(".T", "").replace("^", ""))
            
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
    new_ticker = st.text_input("追加する証券コード", placeholder="例: 9101")
    new_name = st.text_input("表示名（日本語）", placeholder="例: 東北電力")
    if st.button("銘柄を追加"):
        if new_ticker and new_ticker not in st.session_state.config["indices"] and new_ticker not in st.session_state.config["stocks"]:
            st.session_state.config["stocks"].append(new_ticker)
            st.session_state.config["stock_info"][new_ticker] = new_name if new_name else new_ticker.replace(".T", "").replace("^", "")
            save_config(st.session_state.config)
            st.rerun()
    
    st.caption("※証券コードの例:\nトヨタ: 7203\nソニー: 6758\nApple: AAPL")

# --- メイン画面 ---
st.title("📈 株価監視ダッシュボード")
st.write("市場が閉まっている時間は、前日の終値を表示します。")

# 目立つ更新ボタン
if st.button("🚀 最新の株価を更新", type="primary", use_container_width=True):
    with st.spinner("データを取得中..."):
        for ticker in st.session_state.config["indices"] + st.session_state.config["stocks"]:
            price, name = get_stock_data(ticker)
            if price:
                # 前回の価格を取得（なければ現在の価格をセット）
                prev_price = st.session_state.config["history"].get(ticker, {}).get("price", price)
                
                # 履歴を更新
                st.session_state.config["history"][ticker] = {
                    "price": price,
                    "prev_price": prev_price
                }
                # 会社名を保存（未登録の場合のみ）
                if ticker in st.session_state.config["stocks"]:
                    if ticker not in st.session_state.config["stock_info"] or st.session_state.config["stock_info"][ticker] == ticker:
                        st.session_state.config["stock_info"][ticker] = name
        
        save_config(st.session_state.config)
        st.rerun()

st.divider()

# --- 結果の表示 ---
if st.session_state.config["indices"] or st.session_state.config["stocks"]:
    all_items = []
    
    # インデックスの整理
    for ticker in st.session_state.config["indices"]:
        all_items.append({"name": st.session_state.config["labels"].get(ticker, ticker), "symbol": ticker})
    
    # 個別株の整理
    for ticker in st.session_state.config["stocks"]:
        info = st.session_state.config["stock_info"].get(ticker)
        if info:
            all_items.append({"name": f"{info} ({ticker})", "symbol": ticker})
        else:
            all_items.append({"name": ticker.replace(".T", "").replace("^", ""), "symbol": ticker})

    num_items = len(all_items)
    cols_count = min(3, num_items)
    
    for i in range(0, num_items, cols_count):
        cols = st.columns(cols_count)
        for j, item in enumerate(all_items[i:i+cols_count]):
            with cols[j]:
                h = st.session_state.config["history"].get(item["symbol"], {})
                curr = h.get("price")
                prev = h.get("prev_price")
                
                if curr:
                    # 差額の計算
                    if prev and prev != curr:
                        diff = curr - prev
                        diff_pct = (diff / prev) * 100
                        # 色の判定
                        color = "normal"
                        if diff > 0: color = "normal" # Streamlitのmetricは自動で色が変わる
                        
                        # メインの数値
                        st.metric(label=item["name"], value=f"{curr:,.2f}")
                        # 差額のサブテキスト表示
                        st.write(f"前回比: {diff:,.2f} ({diff_pct:+.2f}%)")
                    else:
                        st.metric(label=item["name"], value=f"{curr:,.2f}")
                else:
                    st.write(f"{item['name']}")
                    st.caption("「更新」ボタンを押してください")
else:
    st.info("サイドバーから銘柄を追加してください。")

st.divider()
st.caption("※データ取得に時間がかかる場合があります。")
