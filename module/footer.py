import streamlit as st

def copyright_footer():
    st.markdown(
        """
        <style>
        .footer {
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
        }
        </style>
        <div class="footer">
            &copy; 2025 <a href="mailto:jens.walldorf@uk-halle.de">Jens Walldorf</a> – Diese Simulation dient ausschließlich zu Lehrzwecken.
        </div>
        """,
        unsafe_allow_html=True
    )
