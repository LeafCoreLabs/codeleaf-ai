import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from streamlit_option_menu import option_menu
import plotly.express as px

# ======================
# 🎨 Page Configuration
# ======================
st.set_page_config(
    page_title="CodeLeaf AI",
    page_icon="🌿",
    layout="wide"
)

# ======================
# Theme Colors
# ======================
dark_theme = {
    "background_main": "#0f1116",
    "background_secondary": "#181a1f",
    "text_color": "#e0e0e0",
    "primary_color": "#4ade80",
    "secondary_color": "#9ca3af",
    "border_color": "#4ade80",
    "card_bg": "#1e2128",
    "card_border": "#6b7280"
}

light_theme = {
    "background_main": "#f0f2f6",
    "background_secondary": "#ffffff",
    "text_color": "#333333",
    "primary_color": "#16a34a",
    "secondary_color": "#4b5563",
    "border_color": "#16a34a",
    "card_bg": "#f9fafb",
    "card_border": "#d1d5db"
}

# ======================
# Supported Languages
# ======================
languages = ["python", "c", "cpp", "java", "javascript", "sql"]

# ======================
# Session State Initialization
# ======================
if "history" not in st.session_state:
    st.session_state.history = []
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# ======================
# 🌿 Header and Theme Switch Logic
# ======================
col_logo, col_theme = st.columns([1, 0.1])
with col_theme:
    is_dark = st.toggle("Dark Mode", value=(st.session_state.theme == "dark"), key="theme_toggler")

st.session_state.theme = "dark" if is_dark else "light"
theme = dark_theme if st.session_state.theme == "dark" else light_theme

with col_logo:
    logo_path = "assets/Code_v_dark.png" if st.session_state.theme == "dark" else "assets/Code_v.png"
    st.image(logo_path, width=180)
    st.markdown('<div class="title">🌿 CodeLeaf AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">A Green Leap Forward – Generate Smarter, Greener Code</div>', unsafe_allow_html=True)

# ======================
# 🎨 Custom CSS Styling
# ======================
st.markdown(f"""
<style>
body {{
    background-color: {theme['background_main']};
    color: {theme['text_color']};
}}
.title {{
    font-size: 2.8rem;
    font-weight: bold;
    color: {theme['primary_color']};
    text-align: center;
    margin-bottom: 5px;
}}
.subtitle {{
    font-size: 1.2rem;
    color: {theme['secondary_color']};
    text-align: center;
    margin-bottom: 25px;
}}
.stTextArea textarea {{
    border-radius: 12px;
    border: 1px solid {theme['border_color']};
    padding: 12px;
    font-size: 1rem;
    background-color: {theme['background_secondary']};
    color: {theme['text_color']};
}}
.stButton>button {{
    background: linear-gradient(to right, {theme['primary_color']}, #22c55e);
    color: white;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 1rem;
    font-weight: bold;
    transition: 0.3s;
    border: none;
}}
.stButton>button:hover {{
    background: linear-gradient(to right, #22c55e, #16a34a);
    transform: scale(1.05);
}}
.output-card, .optimization-card {{
    background-color: {theme['card_bg']};
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.3);
}}
.optimization-card {{
    border: 1px solid {theme['card_border']};
}}
.history-card {{
    background-color: {theme['background_secondary']};
    border: 1px solid {theme['card_border']};
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
}}
footer {{
    text-align: center;
    margin-top: 50px;
    font-size: 0.9rem;
    color: {theme['secondary_color']};
}}
footer a {{
    color: {theme['primary_color']};
    text-decoration: none;
}}
footer a:hover {{
    text-decoration: underline;
}}
</style>
""", unsafe_allow_html=True)

# ======================
# ⚡ Menu for Navigation
# ======================
selected_option = option_menu(
    menu_title=None,
    options=["Code Generation", "Code Optimization", "Dashboard"],
    icons=["code-slash", "arrow-repeat", "clipboard-data"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": theme['background_secondary'], "border-radius": "10px"},
        "icon": {"color": theme['primary_color'], "font-size": "18px"},
        "nav-link": {"font-size": "14px", "color": theme['text_color'], "text-align": "center", "margin":"0px", "--hover-color": theme['card_bg']},
        "nav-link-selected": {"background-color": theme['primary_color']},
    }
)

# ======================
# 🚀 Code Generation View
# ======================
if selected_option == "Code Generation":
    prompt = st.text_area(
        "💡 Describe the code you want:",
        height=150,
        placeholder="e.g., A simple calculator...",
        key="codegen_prompt"
    )
    language_gen = st.selectbox("🌐 Select language:", languages, index=0)

    if st.button("⚡ Generate Code", key="generate_code"):
        if prompt.strip():
            with st.spinner("🌱 Growing your code..."):
                try:
                    r = requests.post("http://127.0.0.1:5000/codegen", json={"prompt": prompt, "language": language_gen})
                    r.raise_for_status()
                    data = r.json()
                    language = data.get("language", "python")

                    st.markdown('<div class="output-card">', unsafe_allow_html=True)
                    st.subheader(f"📝 Generated {language.capitalize()} Code")
                    st.code(data["code"], language=language)
                    st.success(f"🌍 Estimated Total CO₂: {data['total_co2_kg']:.6f} kg")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.session_state.history.insert(0, {
                        "type": "generation",
                        "language": language,
                        "prompt": prompt,
                        "code": data["code"],
                        "llm_co2_kg": data["llm_co2_kg"],
                        "execution_co2_kg": data["execution_co2_kg"],
                        "timestamp": datetime.now()
                    })
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please enter a prompt before generating.")

# ======================
# 📈 Code Optimization View
# ======================
elif selected_option == "Code Optimization":
    st.subheader("Unoptimized Code")
    unoptimized_code = st.text_area("Paste your code here:", height=300, key="unoptimized_code_input")
    language_opt = st.selectbox("🌐 Select language:", languages, index=0)

    if st.button("♻️ Optimize & Compare", key="optimize_code"):
        if unoptimized_code.strip():
            with st.spinner("🌿 Optimizing your code..."):
                try:
                    r = requests.post("http://127.0.0.1:5000/optimize", json={"code": unoptimized_code, "language": language_opt})
                    r.raise_for_status()
                    data = r.json()
                    language = data.get("language", "python")

                    st.markdown('<div class="optimization-card">', unsafe_allow_html=True)
                    st.subheader(f"✅ Optimized {language.capitalize()} Code")
                    st.code(data["optimized_code"], language=language)

                    col1, col2, col3 = st.columns(3)
                    with col1: st.info(f"LLM CO₂: {data['llm_co2_kg']:.6f} kg")
                    with col2: st.info(f"Before CO₂: {data['before_co2']:.6f} kg")
                    with col3: st.success(f"After CO₂: {data['after_co2']:.6f} kg")
                    st.markdown(f"**CO₂ Saved:** :green[**{(data['before_co2'] - data['after_co2']):.6f} kg**]")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.session_state.history.insert(0, {
                        "type": "optimization",
                        "language": language,
                        "unoptimized_code": unoptimized_code,
                        "optimized_code": data["optimized_code"],
                        "llm_co2_kg": data["llm_co2_kg"],
                        "co2_before_kg": data["before_co2"],
                        "co2_after_kg": data["after_co2"],
                        "timestamp": datetime.now()
                    })
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please paste some code to optimize.")

# ======================
# 📊 Dashboard View
# ======================
elif selected_option == "Dashboard":
    st.header("📊 Your Green Dashboard")

    if st.session_state.history:
        generation_data = [item for item in st.session_state.history if item["type"] == "generation"]
        if generation_data:
            chart_data = [{"Timestamp": item["timestamp"].strftime("%H:%M:%S"),
                           "Total CO₂ (kg)": item["llm_co2_kg"] + item["execution_co2_kg"]}
                          for item in generation_data]
            df = pd.DataFrame(chart_data)
            st.subheader("Last Code Generations by CO₂ Footprint")
            fig = px.bar(df, x="Timestamp", y="Total CO₂ (kg)", text="Total CO₂ (kg)",
                         color="Total CO₂ (kg)", color_continuous_scale="greens")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📜 History Log")
        for item in st.session_state.history:
            with st.expander(f"🔹 {item['language'].capitalize()} {item['type'].capitalize()} @ {item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"):
                if item["type"] == "generation":
                    st.markdown(f"**Prompt:** {item['prompt']}")
                    st.code(item["code"], language=item["language"])
                    st.info(f"LLM CO₂: {item['llm_co2_kg']:.6f} kg | Execution CO₂: {item['execution_co2_kg']:.6f} kg")
                elif item["type"] == "optimization":
                    st.markdown(f"**Unoptimized Code:**")
                    st.code(item["unoptimized_code"], language=item["language"])
                    st.markdown(f"**Optimized Code:**")
                    st.code(item["optimized_code"], language=item["language"])
                    st.info(f"LLM CO₂: {item['llm_co2_kg']:.6f} kg | Before CO₂: {item['co2_before_kg']:.6f} kg | After CO₂: {item['co2_after_kg']:.6f} kg")
    else:
        st.info("🌿 No history yet. Start generating or optimizing code!")

# ======================
# Footer
# ======================
st.markdown(f"""
<footer>
Made with 💚 by <a href="https://github.com/yourprofile">CodeLeaf Team</a>
</footer>
""", unsafe_allow_html=True)
