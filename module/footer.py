import streamlit as st

from module.fall_config import get_behavior_fix_state, get_fall_fix_state
from module.llm_state import get_provider_label
from module.offline import is_offline


def copyright_footer():
    fall_fixed, scenario = get_fall_fix_state()
    if fall_fixed and scenario:
        fall_status_text = f"Fixierter Fall – {scenario}"
        fall_status_class = "fixed"
    elif fall_fixed:
        fall_status_text = "Fixierter Fall"
        fall_status_class = "fixed"
    else:
        fall_status_text = "Zufälliger Fall"
        fall_status_class = "random"

    behavior_fixed, behavior_value = get_behavior_fix_state()
    if behavior_fixed and behavior_value:
        behavior_status_text = f"Fixiertes Verhalten – {behavior_value}"
        behavior_status_class = "fixed"
    elif behavior_fixed:
        behavior_status_text = "Fixiertes Verhalten"
        behavior_status_class = "fixed"
    else:
        behavior_status_text = "Zufälliges Verhalten"
        behavior_status_class = "random"

    if is_offline():
        llm_status_text = "Offline-Modus (kein LLM)"
        llm_status_class = "offline"
    else:
        llm_status_text = f"LLM-Client: {get_provider_label()}"
        llm_status_class = "provider"

    st.markdown(
        f"""
        <style>
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #f1f1f1;
            color: #666;
            text-align: center;
            padding: 8px;
            font-size: 0.85em;
            border-top: 1px solid #ddd;
            z-index: 100;
        }}
        .footer .status-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px 18px;
            justify-content: center;
            margin-top: 6px;
        }}
        .footer .status-badge {{
            font-weight: 600;
            color: #c0392b;
        }}
        .footer .status-badge.random {{
            color: #666;
        }}
        .footer .status-badge.provider {{
            color: #2c3e50;
        }}
        .footer .status-badge.offline {{
            color: #8e44ad;
        }}
        </style>
        <div class="footer">
            &copy; 2025 – Diese Simulation dient ausschließlich zu Lehrzwecken.
            <div class="status-container">
                <span class="status-badge {fall_status_class}">{fall_status_text}</span>
                <span class="status-badge {behavior_status_class}">{behavior_status_text}</span>
                <span class="status-badge {llm_status_class}">{llm_status_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
