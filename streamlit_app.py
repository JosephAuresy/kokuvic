import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import base64

# Set the title and favicon that appear in the browser's tab bar.
st.set_page_config(
    page_title='Koki Dashboard',
    page_icon=':earth_americas:',  # This is an emoji shortcode. Could be a URL too.
)

# Sidebar for navigation
st.sidebar.title("Navigation")
selected_option = st.sidebar.radio(
    "Select an option:",
    ("Dashboard", "View Report")
)

# Function to process SWAT-MF data
@st.cache_data
def process_swatmf_data(file_path):
    data = []
    current_month = None
    current_year = None

    with open(file_path, 'r') as file:
        for line in file:
            if 'month:' in line:
                parts = line.split()
                try:
                    current_month = int(parts[1])
                    current_year = int(parts[3])
                except (ValueError, IndexError):
                    continue  # Skip if there's an issue parsing month/year
            elif 'Layer' in line:
                continue  # Skip header line
            elif line.strip() == '':
                continue  # Skip empty line
            else:
                parts = line.split()
                if len(parts) == 4:
                    try:
                        layer = int(parts[0])
                        row = int(parts[1])
                        column = int(parts[2])
                        rate = float(parts[3])
                        data.append([current_year, current_month, layer, row, column, rate])
                    except ValueError:
                        continue  # Skip if there's an issue parsing the data

    df = pd.DataFrame(data, columns=['Year', 'Month', 'Layer', 'Row', 'Column', 'Rate'])
    return df

# Path to your data file
DATA_FILENAME = Path(__file__).parent / 'data/swatmf_out_MF_gwsw_monthly.csv'
df = process_swatmf_data(DATA_FILENAME)

# Check if the DataFrame is empty
if df.empty:
    st.error("The data file is empty or could not be read.")
    st.stop()

# Dashboard view
if selected_option == "Dashboard":
    st.title("Groundwater / Surface Water Interactions")

    # Calculate average and standard deviation for each cell (Row, Column) per month
    monthly_stats = df.groupby(['Month', 'Row', 'Column'])['Rate'].agg(['mean', 'std']).reset_index()
    monthly_stats.columns = ['Month', 'Row', 'Column', 'Average Rate', 'Standard Deviation']

    global_min = monthly_stats[['Average Rate', 'Standard Deviation']].min().min()
    global_max = monthly_stats[['Average Rate', 'Standard Deviation']].max().max()
    zmid = global_min / 2

    unique_months = sorted(monthly_stats['Month'].unique())
    climate_options = ['1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
    landuse_options = ['1954', '1972', '2000', '2010', '2020']
    wateruse_options = ['1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']

    # Sidebar dropdowns for scenarios
    selected_climate = st.sidebar.selectbox("Climate Scenario", climate_options, index=6)
    selected_landuse = st.sidebar.selectbox("Land Use Scenario", landuse_options, index=3)
    selected_wateruse = st.sidebar.selectbox("Water Use Scenario", wateruse_options, index=6)

    # Dropdown for selecting month
    selected_month = st.selectbox("Month", unique_months, index=0)

    # Radio buttons for selecting statistic type
    stat_type = st.radio("Statistic Type", ['Average Rate [m3/day]', 'Standard Deviation'], index=0)

    # Filter data for the selected month
    df_filtered = monthly_stats[monthly_stats['Month'] == selected_month]
    max_row = df_filtered['Row'].max()
    max_column = df_filtered['Column'].max()

    grid = np.full((int(max_row), int(max_column)), np.nan)

    for _, row in df_filtered.iterrows():
        r = int(row['Row']) - 1
        c = int(row['Column']) - 1
        if 0 <= r < grid.shape[0] and 0 <= c < grid.shape[1]:
            grid[r, c] = row['Average Rate'] if stat_type == 'Average Rate [m3/day]' else row['Standard Deviation']

    if stat_type == 'Standard Deviation':
        zmin = 0
        zmax = global_max
    else:
        zmin = global_min
        zmax = global_max

    fig = go.Figure(data=go.Heatmap(
        z=grid,
        colorscale='earth_r',
        zmid=zmid,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(title=stat_type),
        hovertemplate='%{z:.2f}<extra></extra>',
    ))

    fig.update_layout(
        title=f'{stat_type} for Month {selected_month}',
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(showticklabels=False, ticks='', showgrid=False),
        yaxis=dict(showticklabels=False, ticks='', autorange='reversed', showgrid=False),
        plot_bgcolor='rgba(240, 240, 240, 0.8)',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12, color='black')
    )

    # Display the heatmap
    st.plotly_chart(fig)

# Report view
elif selected_option == "View Report":
    st.title("PDF Report Viewer")
    
    # Path to the PDF file
    PDF_FILE = Path(__file__).parent / 'data/koki_swatmf_report.pdf'
    
    # Read and encode the PDF file once
    if 'pdf_base64' not in st.session_state:
        with open(PDF_FILE, "rb") as f:
            st.session_state.pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Display the PDF file using an iframe
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{st.session_state.pdf_base64}" width="100%" height="600"></iframe>', 
        unsafe_allow_html=True
    )
    
    # Option to download the PDF file
    st.download_button(
        label="Download PDF",
        data=st.session_state.pdf_base64,
        file_name="koki_swatmf_report.pdf",
        mime="application/pdf",
        key="download_button_report"
    )
