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

# Custom title function
def custom_title(text, size):
    st.markdown(
        f"<h1 style='font-size:{size}px;'>{text}</h1>",
        unsafe_allow_html=True
    )

# Set the width and height based on the device screen size
def get_iframe_dimensions():
    # Default to desktop dimensions; modify if needed for your design
    return "100%", "600"

if selected_option == "Dashboard":
    custom_title("Groundwater / Surface Water Interactions", 28)

    # Add a short description of the project at the bottom of the dashboard
    st.markdown("""
    **Xwulqw’selu Connections** brings people together to learn where streams go dry in the Xwulqw’selu Watershed and how they could begin to flow more. The amount of water flowing in the Koksilah River during summer is dangerously low, leading to streams that feed the river going bone dry. This situation impacts local farmers who struggle to irrigate their crops, while salmon populations face significant survival challenges.

    The **SWAT-MODFLOW model** is employed to assess the interactions between groundwater and surface water, providing insights into the hydrological dynamics of the watershed and identifying strategies for improving water flow in the river system. For more information about the project, please visit [Xwulqw’selu Connections](https://onlineacademiccommunity.uvic.ca/xwulqwselu/).
    """)

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
    stat_type = st.radio("Statistic Type", ['Average Rate [m³/day]', 'Standard Deviation'], index=0)

    # Filter data for the selected month
    df_filtered = monthly_stats[monthly_stats['Month'] == selected_month]
    max_row = df_filtered['Row'].max()
    max_column = df_filtered['Column'].max()

    grid = np.full((int(max_row), int(max_column)), np.nan)

    for _, row in df_filtered.iterrows():
        r = int(row['Row']) - 1
        c = int(row['Column']) - 1
        if 0 <= r < grid.shape[0] and 0 <= c < grid.shape[1]:
            grid[r, c] = row['Average Rate'] if stat_type == 'Average Rate [m³/day]' else row['Standard Deviation']

    if stat_type == 'Standard Deviation':
        zmin = 0
        zmax = global_max
    else:
        zmin = global_min
        zmax = global_max

    colorbar_title = (
        "Average Monthly<br> Groundwater / Surface<br> Water Interaction<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; - To Stream | + To Aquifer<br> [m³/day]"
        if stat_type == 'Average Rate [m³/day]' 
        else '&nbsp;&nbsp;&nbsp;&nbsp;Standard Deviation'
    )
    
    # Calculate the mid point for the color bar (this should be zero)
    zmid = 0
    
    # Create the heatmap figure
    fig = go.Figure(data=go.Heatmap(
        z=grid,
        colorscale='earth_r',
        zmid=zmid,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(
            title=colorbar_title, 
            orientation='h', 
            x=0.5, 
            y=-0.1, 
            xanchor='center', 
            yanchor='top',
            tickvals=[zmin, 0, zmax],  # Specify tick positions
            ticktext=[f'{zmin:.2f}', '0', f'{zmax:.2f}'],  # Custom tick labels
        ),
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
        font=dict(family='Arial, sans-serif', size=8, color='black')
    )

    # Display the heatmap
    st.plotly_chart(fig)

# Report view
elif selected_option == "View Report":
    st.title("Model Validation Report")
    
    # Add a short description
    st.markdown("""
    This report provides a comprehensive validation of the SWAT-MODFLOW model 
    implemented for groundwater and surface water interactions. It includes 
    detailed analysis of the model's performance, statistical metrics, and 
    visualizations that illustrate the model's predictions against observed data.
    """)

    # Path to the PDF file
    PDF_FILE = Path(__file__).parent / 'data/koki_swatmf_report.pdf'
    
    # Read and encode the PDF file
    with open(PDF_FILE, "rb") as f:
        pdf_data = f.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
    
    # Option to download the PDF file (display this button above the PDF viewer)
    st.download_button(
        label="Download PDF",
        data=pdf_data,  # Use raw PDF data for downloading
        file_name="koki_swatmf_report.pdf",
        mime="application/pdf",
        key="download_button_report"
    )

    # Get iframe dimensions
    iframe_width, iframe_height = get_iframe_dimensions()
    
    # Display the PDF file using an iframe
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="{iframe_width}" height="{iframe_height}" style="border:none;"></iframe>', 
        unsafe_allow_html=True
    )
