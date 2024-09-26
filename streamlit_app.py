import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import base64

# Set the title and favicon that appear in the browser's tab bar.
st.set_page_config(
    page_title='Koki Dashboard',
    page_icon=':earth_americas:',
)

# Sidebar for navigation
st.sidebar.title("Navigation")
selected_option = st.sidebar.radio(
    "Select an option:",
    ("Water interactions", "View Report", "Recharge")
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

# Function to read the recharge file
def read_recharge_file(file_path):
    data = {}
    current_year = None
    current_month = None
    reading_data = False

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if 'month:' in line:
                parts = line.split()
                try:
                    current_month = int(parts[1])
                    current_year = int(parts[3])
                    data[(current_year, current_month)] = []
                    reading_data = True  # Start reading grid data
                except (IndexError, ValueError):
                    reading_data = False
            elif line.startswith("Grid data:") or line.startswith("Monthly Averaged Recharge Values"):
                continue
            elif not line:
                continue
            elif reading_data:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        values = [float(v) for v in parts]
                        data[(current_year, current_month)].append(values)
                    except ValueError:
                        continue
            else:
                reading_data = False

    grid_shape = (68, 94)
    for key in data:
        grid_data = np.array(data[key])
        if grid_data.size:
            data[key] = grid_data.reshape(grid_shape)
        else:
            data[key] = np.full(grid_shape, np.nan)

    return data

def compute_monthly_mean(data):
    mean_data = {}
    for (year, month), grid in data.items():
        if month not in mean_data:
            mean_data[month] = []
        mean_data[month].append(grid)
    for month, grids in mean_data.items():
        stacked_grids = np.stack(grids, axis=0)
        mean_data[month] = np.nanmean(stacked_grids, axis=0)
    return mean_data

# Path to your data file
DATA_FILENAME = Path(__file__).parent / 'data/swatmf_out_MF_gwsw_monthly.csv'
df = process_swatmf_data(DATA_FILENAME)

# Path to recharge data
RECHARGE_FILENAME = Path(__file__).parent / 'data/swatmf_out_MF_recharge_monthly.txt'
recharge_data = read_recharge_file(RECHARGE_FILENAME)
monthly_recharge_means = compute_monthly_mean(recharge_data)

# Custom title function
def custom_title(text, size):
    st.markdown(
        f"<h1 style='font-size:{size}px;'>{text}</h1>",
        unsafe_allow_html=True
    )

# Set the width and height based on the device screen size
def get_iframe_dimensions():
    return "100%", "600"

if selected_option == "Water interactions":
    custom_title("Groundwater / Surface Water Interactions", 28)

    st.markdown("""
    **Xwulqw’selu Connections** brings people together to learn where streams go dry in the Xwulqw’selu Watershed and how they could begin to flow more. The amount of water flowing in the Koksilah River during summer is dangerously low, leading to streams that feed the river going bone dry. This situation impacts local farmers who struggle to irrigate their crops, while salmon populations face significant survival challenges.

    The **SWAT-MODFLOW model** is employed to assess the interactions between groundwater and surface water, providing insights into the hydrological dynamics of the watershed and identifying strategies for improving water flow in the river system. For more information about the project, please visit [Xwulqw’selu Connections](https://onlineacademiccommunity.uvic.ca/xwulqwselu/).
    """)

    monthly_stats = df.groupby(['Month', 'Row', 'Column'])['Rate'].agg(['mean', 'std']).reset_index()
    monthly_stats.columns = ['Month', 'Row', 'Column', 'Average Rate', 'Standard Deviation']

    global_min = monthly_stats[['Average Rate', 'Standard Deviation']].min().min()
    global_max = monthly_stats[['Average Rate', 'Standard Deviation']].max().max()

    unique_months = sorted(monthly_stats['Month'].unique())

    selected_month = st.selectbox("Month", unique_months, index=0)
    stat_type = st.radio("Statistic Type", ['Average Rate [m³/day]', 'Standard Deviation'], index=0)

    df_filtered = monthly_stats[monthly_stats['Month'] == selected_month]
    grid = np.full((int(df_filtered['Row'].max()), int(df_filtered['Column'].max())), np.nan)

    for _, row in df_filtered.iterrows():
        grid[int(row['Row']) - 1, int(row['Column']) - 1] = row['Average Rate'] if stat_type == 'Average Rate [m³/day]' else row['Standard Deviation']

    # Define color scale and boundaries for heatmap
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

    # Calculate the midpoint for the color bar (usually zero)
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
    
elif selected_option == "Recharge":
    custom_title("Recharge Data", 28)

    # Dropdown to select month for recharge data visualization
    selected_month = st.selectbox("Select Month for Recharge", list(monthly_recharge_means.keys()))
    recharge_grid = monthly_recharge_means[selected_month]

    # Create a custom colorscale where zero values are black
    custom_colorscale = [
        [0.0, 'white'],       # Zero mapped to black
        [0.00001, 'powderblue'],  # Small values start as light powder blue
        [0.5, 'lightskyblue'],    # Mid-range values are light sky blue
        [1.0, 'blue']         # Maximum values are dark blue
    ]

    # Create heatmap for the selected recharge month
    fig = go.Figure(data=go.Heatmap(
        z=recharge_grid,
        colorscale=custom_colorscale,  # Using the custom color scale
        zmin=0,                        # Set minimum value to 0
        zmax=max(map(max, recharge_grid)),  # Set maximum value from data
        zmid=0                         # Center the color scale around zero
    ))

    # Update the layout of the heatmap
    fig.update_layout(
        title=f'Recharge Data for Month {selected_month}',  # Title of the heatmap
        xaxis_title=None,    # No title for x-axis
        yaxis_title=None,    # No title for y-axis
        xaxis=dict(
            showticklabels=False,  # Hide x-axis labels
            ticks='',              # No ticks on x-axis
            showgrid=False         # Hide grid on x-axis
        ),
        yaxis=dict(
            showticklabels=False,  # Hide y-axis labels
            ticks='',              # No ticks on y-axis
            autorange='reversed',  # Reverse y-axis order
            showgrid=False         # Hide grid on y-axis
        ),
        plot_bgcolor='rgba(240, 240, 240, 0.8)',  # Keep plot background light
        paper_bgcolor='white',                    # Keep the outer paper background white
        font=dict(family='Arial, sans-serif', size=8, color='black'),  # Font color remains black
    )

    # Display the recharge heatmap
    st.plotly_chart(fig)

elif selected_option == "View Report":
    st.title("Model Validation Report")

    # Add a short description
    st.markdown("""
    This report provides a comprehensive validation of the SWAT-MODFLOW model 
    implemented for groundwater and surface water interactions. It includes 
    detailed analysis of the model's performance, statistical metrics, and 
    visualizations that illustrate the model's predictions against observed data.
    """)

    PDF_FILE = Path(__file__).parent / 'data/koki_swatmf_report.pdf'
    with open(PDF_FILE, "rb") as f:
        pdf_data = f.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

    st.download_button(
        label="Download PDF",
        data=pdf_data,
        file_name="koki_swatmf_report.pdf",
        mime="application/pdf"
    )
    
    iframe_width, iframe_height = get_iframe_dimensions()
    st.markdown(f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="{iframe_width}" height="{iframe_height}" style="border:none;"></iframe>', unsafe_allow_html=True)
