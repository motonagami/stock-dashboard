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

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"config.json への保存エラー: {e}")

config = load_config()

# --- セッション状態の初期化 ---
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

# 画面を中央に寄せるためのレイアウト
col_left, col_mid, col_right = st.columns([1, 4, 1])

with col_mid:
    st.title("📈 株価監視ダッシュボード")
    st.write("※PCで管理アプリを使い config.json を更新することで常設銘柄が反映されます。")
    st.write("---")

    # --- サイドバー：銘柄管理（追加・削除のみのシンプルな画面） ---
    with st.sidebar:
        st.title("⚙️ 銘柄設定")
        with st.expander("常設銘柄の追加・削除", expanded=True):
            new_name = st.text_input("日本語名（例：トヨタ自動車）")
            new_code = st.text_input("コード（例：7203）")
            
            if st.button("追加", type="primary"):
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
                        st.warning("既に登録されています。")
                else:
                    st.warning("名前とコードを入力してください")

        st.write("---")
        st.subheader("当日のみの追加")
        with st.expander("一時的な銘柄追加", expanded=True):
            temp_name = st.text_input("日本語名（例：一時確認）")
            temp_code = st.text_input("コード（例：9101）")
            
            if st.button("一時追加", type="secondary"):
                if temp_name and temp_code:
                    symbol = temp_code if "." in temp_code else f"{temp_code}.T"
                    if not any(s["symbol"] == symbol for s in config["stocks"]) and \
                       not any(s["symbol"] == symbol for s in st.session_state.today_stocks):
                        
                        st.session_state.today_stocks.append({"name": temp_name, "symbol": symbol})
                        st.success(f"{temp_name} を追加しました（ブラウザ更新まで保持）")
                        st.rerun()
                    else:
                        st.warning("既にリストに含まれています。")

        if st.session_state.today_stocks:
            st.write("---")
            for i, stock in enumerate(st.session_state.today_stocks):
                c1, c2 = st.columns([3, 1])
                c1.write(f"{stock['name']} ({stock['symbol']})")
                if c2.button("削除", key=f"del_tmp_{i}"):
                    st.session_state.today_stocks.pop(i)
                    st.rerun()

    # --- メイン画面：更新ボタン ---
    status_placeholder = st.empty()

    if st.button("🔄 株価を更新", type="primary"):
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

    # カードの表示ループ
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
                color = "#888888" # 変化なし
            
            display_diff = f"{diff_amount:,.0f} ({diff_percent:+.2f}%)"

        # --- アプリ2のカード形式レイアウト ---
        st.markdown(f"""
        <div style="
            background-color: #f0f2f6;
            padding: 25px;
            border-radius: 20px;
            margin-bottom: 20px;
            border: 2px solid #e0e0e0;
            text-align: center;
            font-family: sans-serif;
        ">
            <p style="font-size: 40px; margin: 0; color: #18610c; font-weight: bold;">{name}</p>
            <p style="font-size: 60px; font-weight: bold; margin: 15px 0; color: #000;">
                {current_price if current_price else '--':,}
            </p>
            <p style="font-size: 40px; font-weight: bold; margin: 8px 0; color: {color};">
                {display_diff}
            </p>
            <p style="font-size: 30px; margin: 5px 0 0 0; color: #641075; font-weight: bold;">
                前日終値：{prev_day_close if prev_day_close else '--':,}
            </p>
        </div>
        """, unsafe_allow_html=True)

with st.expander("詳細ログ (デバッグ用)"):
    st.write("現在の履歴:", config["history"])
    st.write("前日の終値履歴:", config["prev_day_close_history"])
    st.write("銘柄リスト:", config["stocks"])
