import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Koki dashboard',
    page_icon=':earth_americas:',  # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
# Define the function to read and process data
def process_swatmf_data(file_path):
    """
    Reads the SWAT-MF groundwater/surface water interaction data and returns a DataFrame
    with Year, Month, Layer, Row, Column, and Rate information.
    """
    # Initialize lists to hold data
    data = []
    current_month = None
    current_year = None

    # Read the file line by line
    with open(file_path, 'r') as file:
        for line in file:
            if 'month:' in line:
                # Extract month and year
                parts = line.split()
                try:
                    current_month = int(parts[1])
                    current_year = int(parts[3])
                except (ValueError, IndexError):
                    continue  # Skip if there's an issue parsing month/year
            elif 'Layer' in line:
                # Read header line (skip)
                continue
            elif line.strip() == '':
                # Empty line (skip)
                continue
            else:
                # Extract data
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

    # Convert data to DataFrame
    df = pd.DataFrame(data, columns=['Year', 'Month', 'Layer', 'Row', 'Column', 'Rate'])
    
    return df

# Use Path to specify the location of your data file
DATA_FILENAME = Path(__file__).parent / 'data/swatmf_out_MF_gwsw_monthly.csv'

# Call the function to get the processed data
df = process_swatmf_data(DATA_FILENAME)

# Check if the DataFrame is empty
if df.empty:
    st.error("The data file is empty or could not be read.")
    st.stop()

# -----------------------------------------------------------------------------
# Draw the actual page

st.title("Groundwater / Surface Water Interactions")

# Calculate average and standard deviation for each cell (Row, Column) per month
monthly_stats = df.groupby(['Month', 'Row', 'Column'])['Rate'].agg(['mean', 'std']).reset_index()
monthly_stats.columns = ['Month', 'Row', 'Column', 'Average Rate', 'Standard Deviation']

# Get global min and max to keep the colorbar consistent across months
global_min = monthly_stats[['Average Rate', 'Standard Deviation']].min().min()
global_max = monthly_stats[['Average Rate', 'Standard Deviation']].max().max()

# Set zmid to stretch positive values more
zmid = global_min / 2  # Adjust to emphasize positive values

# Get unique months
unique_months = sorted(monthly_stats['Month'].unique())

# Climate, Land Use, and Water Use options
climate_options = ['1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
landuse_options = ['1954', '1972', '2000', '2010', '2020']
wateruse_options = ['1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']

# Dropdowns for selecting scenarios
selected_climate = st.selectbox("Climate Scenario", climate_options, index=6)
selected_landuse = st.selectbox("Land Use Scenario", landuse_options, index=3)
selected_wateruse = st.selectbox("Water Use Scenario", wateruse_options, index=6)

# Dropdown for selecting month
selected_month = st.selectbox("Month", unique_months, index=0)

# Radio buttons for selecting statistic type
stat_type = st.radio("Statistic Type", ['Average Rate [m3/day]', 'Standard Deviation'], index=0)

# Filter data for the selected month
df_filtered = monthly_stats[monthly_stats['Month'] == selected_month]

# Identify maximum rows and columns
max_row = df_filtered['Row'].max()
max_column = df_filtered['Column'].max()

# Create an empty grid with maximum rows and columns
grid = np.full((int(max_row), int(max_column)), np.nan)  # Using NaN to represent no data

# Fill the grid with the selected statistic values
for _, row in df_filtered.iterrows():
    r = int(row['Row']) - 1
    c = int(row['Column']) - 1
    if 0 <= r < grid.shape[0] and 0 <= c < grid.shape[1]:
        grid[r, c] = row['Average Rate'] if stat_type == 'Average Rate [m3/day]' else row['Standard Deviation']

# Adjust zmin and zmax for consistent color scaling
if stat_type == 'Standard Deviation':
    zmin = 0  # Standard deviation cannot be negative
    zmax = global_max
else:
    zmin = global_min
    zmax = global_max

# Create heatmap with global min, max and a midpoint to stretch positive values
fig = go.Figure(data=go.Heatmap(
    z=grid,
    colorscale='earth_r',  # Color scale
    zmid=zmid,  # Stretch to emphasize positive values
    zmin=zmin,  # Keep colorbar consistent across months
    zmax=zmax,
    colorbar=dict(title=stat_type),
    hovertemplate='%{z:.2f}<extra></extra>',  # Display actual values
))

# Update the layout with a custom title
fig.update_layout(
    title=f'{stat_type} for Month {selected_month}',
    xaxis_title=None,  # Remove X-axis title
    yaxis_title=None,  # Remove Y-axis title
    xaxis=dict(showticklabels=False, ticks='', showgrid=False),
    yaxis=dict(showticklabels=False, ticks='', autorange='reversed', showgrid=False),
    plot_bgcolor='rgba(240, 240, 240, 0.8)',  # Light gray background for the plot
    paper_bgcolor='white',  # White background for the page
    font=dict(family='Arial, sans-serif', size=12, color='black')
)

# Display the heatmap
st.plotly_chart(fig)
