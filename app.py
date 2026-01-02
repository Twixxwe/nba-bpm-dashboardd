import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="NBA BPM Dashboard", layout="wide")
st.title("🏀 NBA BPM Impact Dashboard")
st.markdown("---")

# Function to load data
@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_nba_data():
    try:
        # Load the advanced stats table
        url = "https://www.basketball-reference.com/leagues/NBA_2026_advanced.html"
        tables = pd.read_html(url)
        df = tables[0]
        
        # Remove header rows that repeat in the data
        df = df[df['Rk'] != 'Rk'].copy()
        
        # Clean up column names - they might have spaces
        df.columns = df.columns.str.strip()
        
        # Find BPM column (could be 'BPM' or 'BPM*')
        bpm_column = None
        for col in df.columns:
            if 'BPM' in col:
                bpm_column = col
                break
        
        if bpm_column is None:
            st.error("Could not find BPM column in the data!")
            return None
        
        # Select and rename columns
        df = df[['Player', 'Team', 'G', 'MP', bpm_column]].copy()
        df = df.rename(columns={bpm_column: 'BPM', 'Team': 'Team'})
        
        # Convert to numeric, handle errors
        df['G'] = pd.to_numeric(df['G'], errors='coerce')
        df['MP'] = pd.to_numeric(df['MP'], errors='coerce')
        df['BPM'] = pd.to_numeric(df['BPM'], errors='coerce')
        
        # Drop rows with missing values
        df = df.dropna()
        
        # Calculate MPG and Impact
        df['MPG'] = df['MP'] / df['G']
        df['Impact'] = (df['BPM'] / 100) * df['MPG'] * 2.083
        
        # Round values for display
        df['MPG'] = df['MPG'].round(1)
        df['Impact'] = df['Impact'].round(3)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load the data
with st.spinner('Loading NBA data from Basketball-Reference...'):
    nba_data = load_nba_data()

if nba_data is None:
    st.stop()

# Sidebar for controls
st.sidebar.header("📊 Dashboard Controls")

# Injury management
st.sidebar.subheader("🩹 Injury Management")
injured_players = st.sidebar.multiselect(
    "Select injured players:",
    options=nba_data['Player'].tolist(),
    help="Selected players will have their impact set to 0"
)

# Create a working copy for calculations
working_data = nba_data.copy()

# Apply injuries
if injured_players:
    working_data.loc[working_data['Player'].isin(injured_players), 'Impact'] = 0
    st.sidebar.success(f"{len(injured_players)} player(s) marked as injured")

# Filter options
st.sidebar.subheader("🔍 Filters")
min_games = st.sidebar.slider("Minimum games played:", 1, 82, 20)
filtered_data = working_data[working_data['G'] >= min_games]

# Team selection
st.sidebar.subheader("🏀 Matchup Selection")
all_teams = sorted(filtered_data['Team'].unique())

col1, col2 = st.sidebar.columns(2)
with col1:
    team1 = st.selectbox("Team 1", all_teams, index=0 if 'LAL' in all_teams else 0)
with col2:
    # Default to a different team for Team 2
    team2_default = 'BOS' if 'BOS' in all_teams else all_teams[1] if len(all_teams) > 1 else all_teams[0]
    team2 = st.selectbox("Team 2", all_teams, index=all_teams.index(team2_default) if team2_default in all_teams else 0)

# Main content area
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.subheader(f"📈 {team1} vs {team2} Matchup")
    
    # Calculate team totals
    team1_data = filtered_data[filtered_data['Team'] == team1]
    team2_data = filtered_data[filtered_data['Team'] == team2]
    
    team1_impact = team1_data['Impact'].sum()
    team2_impact = team2_data['Impact'].sum()
    advantage = team1_impact - team2_impact
    
    # Display matchup metrics
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric(f"{team1} Total Impact", f"{team1_impact:.2f}")
    with metric_col2:
        st.metric(f"{team2} Total Impact", f"{team2_impact:.2f}")
    with metric_col3:
        st.metric("Projected Advantage", 
                 f"{advantage:.2f}",
                 delta=f"{team1} by {abs(advantage):.2f}" if advantage > 0 else f"{team2} by {abs(advantage):.2f}",
                 delta_color="normal" if advantage > 0 else "inverse")

with col2:
    st.subheader("📊 Team Impact")
    team_impacts = pd.DataFrame({
        'Team': [team1, team2],
        'Impact': [team1_impact, team2_impact]
    })
    st.bar_chart(team_impacts.set_index('Team'))

with col3:
    st.subheader("🎯 Prediction")
    if advantage > 1:
        st.success(f"**{team1} favored** by {advantage:.2f} points")
    elif advantage < -1:
        st.error(f"**{team2} favored** by {abs(advantage):.2f} points")
    else:
        st.info("**Close matchup** - within 1 point")

# Player tables
st.markdown("---")
st.subheader("👥 Player Contributions")

# Combined player table
combined_data = pd.concat([team1_data, team2_data])

# Sorting options
sort_col1, sort_col2 = st.columns([1, 2])
with sort_col1:
    sort_by = st.selectbox(
        "Sort by:",
        ['Team', 'Player', 'Impact', 'BPM', 'MPG', 'G']
    )
with sort_col2:
    sort_order = st.radio(
        "Sort order:",
        ['Descending', 'Ascending'],
        horizontal=True
    )

# Apply sorting
sorted_data = combined_data.sort_values(
    by=sort_by,
    ascending=(sort_order == 'Ascending')
)

# Display the table
st.dataframe(
    sorted_data[['Team', 'Player', 'G', 'MPG', 'BPM', 'Impact']].reset_index(drop=True),
    use_container_width=True,
    column_config={
        "Team": st.column_config.TextColumn("Team", width="small"),
        "Player": st.column_config.TextColumn("Player", width="medium"),
        "G": st.column_config.NumberColumn("Games", format="%d"),
        "MPG": st.column_config.NumberColumn("MPG", format="%.1f"),
        "BPM": st.column_config.NumberColumn("BPM", format="%.1f"),
        "Impact": st.column_config.NumberColumn("Impact", format="%.3f")
    }
)

# Show top players
st.markdown("---")
st.subheader("⭐ Top Performers")

top_col1, top_col2 = st.columns(2)
with top_col1:
    st.write(f"**{team1} Top 5:**")
    top_team1 = team1_data.nlargest(5, 'Impact')[['Player', 'Impact']]
    st.dataframe(top_team1.set_index('Player'), use_container_width=True)

with top_col2:
    st.write(f"**{team2} Top 5:**")
    top_team2 = team2_data.nlargest(5, 'Impact')[['Player', 'Impact']]
    st.dataframe(top_team2.set_index('Player'), use_container_width=True)

# Data source
st.markdown("---")
st.caption("📊 Data sourced from Basketball-Reference.com | Impact = (BPM/100) × MPG × 2.083")
st.caption("⚠️ Note: This is a simplified model for demonstration purposes")
