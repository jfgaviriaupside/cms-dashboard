import streamlit as st
import pandas as pd
import plotly.express as px
import plotly as pl
from datetime import datetime
import pytz

# Initial setup
st.set_page_config(page_title="CMS Performance Dashboard", layout="wide")
st.title("CMS Performance Dashboard")

# Define consistent color scheme
COLOR_SCHEME = px.colors.qualitative.Set3  # or any other color scheme you prefer

# Add timestamp
mexico_tz = pytz.timezone('America/Mexico_City')
current_time = datetime.now(mexico_tz)
st.caption(f"Last Updated: {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

# Add this after the validate_data function and before loading the base data

def calculate_percentage_change(old_value, new_value):
    """Calculate the percentage change between two values."""
    if old_value == 0:
        return None
    return ((new_value - old_value) / old_value) * 100

# Load base data
@st.cache_data
def load_base_data():
    try:
        # Attempt to load the base data file
        base_data = pd.read_excel("base_data (3).xlsx")
        
        # Verify the required columns exist
        required_columns = ['TRANSFORMED DATE', 'PROCEDURE', 'REFERRING PHYSICIAN', 'Data Set']
        missing_columns = [col for col in required_columns if col not in base_data.columns]
        
        if missing_columns:
            st.error(f"Base data is missing required columns: {', '.join(missing_columns)}")
            return None
            
        # Convert date column
        try:
            base_data['TRANSFORMED DATE'] = pd.to_datetime(base_data['TRANSFORMED DATE'])
        except Exception as e:
            st.error(f"Error converting dates in base data: {str(e)}")
            return None
            
        st.success(f"Successfully loaded base data with {len(base_data)} records")
        return base_data
        
    except FileNotFoundError:
        st.error("Could not find base_data.xlsx in the current directory. Please ensure the file exists.")
        return None
    except Exception as e:
        st.error(f"Error loading base data: {str(e)}")
        return None

@st.cache_data
def load_top_200_docs():
    try:
        # Load the Top 200 Doctors file
        top_200 = pd.read_excel("Top_200_doctores.xlsx")
        
        # Check if the responsible column exists (try different possible names)
        responsible_column = None
        possible_names = ['RESPONSABLE', 'Responsable', 'RESPONSIBLE', 'Responsible']
        
        for name in possible_names:
            if name in top_200.columns:
                responsible_column = name
                break
        
        if responsible_column is None:
            st.error("Could not find the responsible person column in the Top 200 Doctors file.")
            return None
        
        # Store the correct column name for later use
        top_200['correct_responsible_column'] = responsible_column
        
        return top_200
    except Exception as e:
        st.error(f"Error loading Top 200 Doctors file: {str(e)}")
        return None

# Load base data
base_data = load_base_data()
top_200_docs = load_top_200_docs()

# Function to validate new data
def validate_data(new_data, base_data):
    validation_errors = []
    
    # Check if columns match
    missing_cols = set(base_data.columns) - set(new_data.columns)
    if missing_cols:
        validation_errors.append(f"Missing columns in uploaded file: {missing_cols}")
    
    # Check data types of key columns
    required_types = {
        'TRANSFORMED DATE': 'datetime64[ns]',
        'PROCEDURE': 'object',
        'REFERRING PHYSICIAN': 'object',
        'Data Set': 'object'
    }
    
    for col, dtype in required_types.items():
        if col in new_data.columns:
            try:
                new_data[col] = new_data[col].astype(dtype)
            except Exception as e:
                validation_errors.append(f"Error converting column {col} to {dtype}: {str(e)}")
    
    if validation_errors:
        for error in validation_errors:
            st.error(error)
        return False
    
    return True

if base_data is not None:
    # Display base data info
    st.sidebar.info(f"""
    Base Data Summary:
    - Total Records: {len(base_data):,}
    - Date Range: {base_data['TRANSFORMED DATE'].min().strftime('%Y-%m-%d')} to {base_data['TRANSFORMED DATE'].max().strftime('%Y-%m-%d')}
    - Unique Doctors: {base_data['REFERRING PHYSICIAN'].nunique():,}
    """)
    
    # Upload new data
    st.subheader("Upload New Data")
    uploaded_file = st.file_uploader(
        "Upload additional data file (Excel or CSV)", 
        type=["xlsx", "csv"],
        help="File must have the same column structure as the base data"
    )

    if uploaded_file:
        with st.spinner('Processing uploaded data...'):
            # Load new data
            try:
                if uploaded_file.name.endswith(".xlsx"):
                    new_data = pd.read_excel(uploaded_file)
                else:
                    new_data = pd.read_csv(uploaded_file)
                
                st.info(f"Attempting to process {len(new_data):,} new records...")
                
                # Validate new data
                if validate_data(new_data, base_data):
                    # Combine data
                    data = pd.concat([base_data, new_data], ignore_index=True)
                    
                    # Remove duplicates if any
                    initial_len = len(data)
                    data = data.drop_duplicates()
                    duplicates_removed = initial_len - len(data)
                    
                    # Sort by date
                    data = data.sort_values('TRANSFORMED DATE')
                    
                    st.success(f"""
                    Successfully processed new data:
                    - Records added: {len(new_data):,}
                    - Duplicates removed: {duplicates_removed:,}
                    - Total records now: {len(data):,}
                    """)
                    
                    # Display summary of new data
                    st.write("Summary of new data:")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("New Records", f"{len(new_data):,}")
                    with col2:
                        st.metric("Date Range", f"{new_data['TRANSFORMED DATE'].min().strftime('%Y-%m-%d')} to {new_data['TRANSFORMED DATE'].max().strftime('%Y-%m-%d')}")
                    with col3:
                        st.metric("Unique Doctors", f"{new_data['REFERRING PHYSICIAN'].nunique():,}")
                else:
                    st.error("Please fix the data format issues before proceeding")
                    st.stop()
                    
            except Exception as e:
                st.error(f"Error processing uploaded file: {str(e)}")
                st.stop()
    else:
        # If no new data uploaded, use base data
        data = base_data.copy()

    # Continue with data preprocessing
    data['Month'] = data['TRANSFORMED DATE'].dt.to_period('M').astype(str)
    data['Day of Month'] = data['TRANSFORMED DATE'].dt.day
    data['Day of Week'] = data['TRANSFORMED DATE'].dt.day_name()
    
    # Display current data summary in sidebar
    st.sidebar.success(f"""
    Current Data Summary:
    - Total Records: {len(data):,}
    - Date Range: {data['TRANSFORMED DATE'].min().strftime('%Y-%m-%d')} to {data['TRANSFORMED DATE'].max().strftime('%Y-%m-%d')}
    - Unique Doctors: {data['REFERRING PHYSICIAN'].nunique():,}
    - Months Available: {data['Month'].nunique()}
    """)

else:
    st.error("""
    No base data available. Please ensure:
    1. The file 'base_data.xlsx' exists in the app directory
    2. The file contains the required columns
    3. The data is properly formatted
    """)
    st.stop()

# Filter working days
working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
working_data = data[data['Day of Week'].isin(working_days)]

# Aggregations
month_summary = (
    working_data
    .groupby(['Month', 'PROCEDURE'])
    .size()
    .reset_index(name='Count')
)

# Create tabs for navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "One Month Overview", 
    "Two Month Comparison", 
    "Top 200 Doctors Performance and Comparison",
    "Top 200 Doctors Category Analysis"
])

with tab1:
    # First Tab: One Month Overview
    st.subheader("One Month Overview")
    
    # Add instructions
    st.info("""
    📊 **How to use this tab:**
    1. Select a month from the dropdown menu below
    2. View the monthly metrics (total procedures, referring doctors, and insurances)
    3. Explore the procedure distribution chart
    4. Check the top referring doctors for the selected month
    5. Analyze insurance distribution through the pie chart
    
    This tab provides a comprehensive overview of all activity for a single selected month.
    """)
    
    # Select month for detailed view
    selected_month = st.selectbox("Select Month", month_summary['Month'].unique())
    filtered_data = month_summary[month_summary['Month'] == selected_month]
    
    # Filter working data for selected month
    monthly_data = working_data[working_data['Month'] == selected_month]
    
    # Big number metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_procedures = len(monthly_data)
        st.metric("Total Monthly Procedures", total_procedures)
    
    with col2:
        unique_doctors = monthly_data['REFERRING PHYSICIAN'].nunique()
        st.metric("Total Unique Referring Doctors", unique_doctors)
    
    with col3:
        unique_insurances = monthly_data['Data Set'].nunique()
        st.metric("Total Unique Insurances", unique_insurances)
    
    # Interactive Bar Chart - Procedures by Count
    st.subheader("Procedures Distribution")
    fig = px.bar(filtered_data, 
                x='PROCEDURE', 
                y='Count', 
                title=f"Procedures Count for {selected_month}",
                color_discrete_sequence=COLOR_SCHEME)
    st.plotly_chart(fig, use_container_width=True)
    
    # Top Referring Doctors
    st.subheader("Top Referring Doctors")
    top_doctors = (
        monthly_data.groupby('REFERRING PHYSICIAN')
        .size()
        .sort_values(ascending=False)
        .reset_index(name='Count')
        .head(10)
    )
    
    fig_doctors = px.bar(top_doctors, 
                       x='REFERRING PHYSICIAN', 
                       y='Count', 
                       title=f"Top 10 Referring Doctors - {selected_month}",
                       color_discrete_sequence=COLOR_SCHEME)
    st.plotly_chart(fig_doctors, use_container_width=True)
    
    # Top Insurances
    st.subheader("Top Insurances")
    top_insurances = (
        monthly_data.groupby('Data Set')
        .size()
        .sort_values(ascending=False)
        .reset_index(name='Count')
        .head(10)
    )
    
    fig_insurances = px.pie(top_insurances, 
                          names='Data Set', 
                          values='Count', 
                          title=f"Top 10 Insurances by Procedure Count - {selected_month}",
                          color_discrete_sequence=COLOR_SCHEME)
    st.plotly_chart(fig_insurances, use_container_width=True)

with tab2:
    # Second Tab: Two Month Comparison
    st.subheader("Two Month Comparison")
    
    # Add instructions
    st.info("""
    📊 **How to use this tab:**
    1. Select two months to compare using the dropdown menu
    2. Optionally filter by specific procedure type
    3. Compare key metrics between the two months:
       - Total procedures
       - Number of physicians
       - Insurance diversity
    4. Analyze the changes in referring doctors:
       - Top performers comparison
       - Biggest gainers and decreases
    5. Compare insurance distributions between months
    
    This tab helps identify trends and changes between any two selected months.
    """)
    
    # Select months for comparison (limit to 2)
    col1, col2 = st.columns([2, 1])
    with col1:
        compare_months = st.multiselect(
            "Select Two Months to Compare",
            options=working_data['Month'].unique(),
            default=working_data['Month'].unique()[-2:],  # Default to last two months
            max_selections=2
        )
    
    # Ensure exactly two months are selected
    if len(compare_months) != 2:
        st.warning("Please select exactly two months to compare")
    else:
        # Optional procedure filter
        with col2:
            procedure_filter = st.selectbox(
                "Filter by Procedure (Optional)",
                options=["All Procedures"] + list(working_data['PROCEDURE'].unique())
            )
        
        # Filter data based on selections
        if procedure_filter == "All Procedures":
            compare_data = working_data[working_data['Month'].isin(compare_months)]
        else:
            compare_data = working_data[
                (working_data['Month'].isin(compare_months)) & 
                (working_data['PROCEDURE'] == procedure_filter)
            ]
        
        # Monthly comparison metrics
        st.subheader("Monthly Comparison")
        col1, col2, col3 = st.columns(3)
        
        # Calculate metrics for each month
        metrics = {}
        for month in compare_months:
            month_data = compare_data[compare_data['Month'] == month]
            metrics[month] = {
                'Total Procedures': len(month_data),
                'Unique Physicians': month_data['REFERRING PHYSICIAN'].nunique(),
                'Unique Insurances': month_data['Data Set'].nunique()
            }
        
        # Display metrics with month-over-month comparison
        with col1:
            pct_change = calculate_percentage_change(
                metrics[compare_months[0]]['Total Procedures'],
                metrics[compare_months[1]]['Total Procedures']
            )
            delta_text = f"{metrics[compare_months[1]]['Total Procedures'] - metrics[compare_months[0]]['Total Procedures']} ({pct_change:.1f}%)" if pct_change is not None else "N/A"
            st.metric(
                "Total Procedures",
                metrics[compare_months[1]]['Total Procedures'],
                delta=delta_text
            )
        with col2:
            pct_change = calculate_percentage_change(
                metrics[compare_months[0]]['Unique Physicians'],
                metrics[compare_months[1]]['Unique Physicians']
            )
            delta_text = f"{metrics[compare_months[1]]['Unique Physicians'] - metrics[compare_months[0]]['Unique Physicians']} ({pct_change:.1f}%)" if pct_change is not None else "N/A"
            st.metric(
                "Unique Physicians",
                metrics[compare_months[1]]['Unique Physicians'],
                metrics[compare_months[1]]['Unique Physicians'] - metrics[compare_months[0]]['Unique Physicians']
            )
        with col3:
            st.metric(
                "Unique Insurances",
                metrics[compare_months[1]]['Unique Insurances'],
                metrics[compare_months[1]]['Unique Insurances'] - metrics[compare_months[0]]['Unique Insurances']
            )
        
        # Top 10 Referring Doctors comparison
        st.subheader("Top 10 Referring Doctors")
        
        # Get top 10 doctors from newest month
        newest_month = compare_months[1]
        older_month = compare_months[0]
        
        newest_month_data = compare_data[compare_data['Month'] == newest_month]
        older_month_data = compare_data[compare_data['Month'] == older_month]
        
        # Get counts for both months
        newest_month_counts = newest_month_data.groupby('REFERRING PHYSICIAN').size()
        older_month_counts = older_month_data.groupby('REFERRING PHYSICIAN').size()
        
        # Get top 10 doctors from newest month
        top_10_doctors = newest_month_counts.nlargest(10)
        
        # Create comparison dataframe with proper handling of missing doctors
        doctor_comparison = pd.DataFrame({
            older_month: [older_month_counts.get(doctor, 0) for doctor in top_10_doctors.index],
            newest_month: top_10_doctors.values
        }, index=top_10_doctors.index)
        
        # Create grouped bar chart
        fig_doctors = pl.graph_objects.Figure(data=[
            pl.graph_objects.Bar(
                name=older_month,
                x=doctor_comparison.index,
                y=doctor_comparison[older_month],
                text=doctor_comparison[older_month].round(0).astype(int),
                textposition='auto',
                marker_color=COLOR_SCHEME[0]
            ),
            pl.graph_objects.Bar(
                name=newest_month,
                x=doctor_comparison.index,
                y=doctor_comparison[newest_month],
                text=doctor_comparison[newest_month].round(0).astype(int),
                textposition='auto',
                marker_color=COLOR_SCHEME[1]
            )
        ])
        
        fig_doctors.update_layout(
            barmode='group',
            title=f"Top 10 Referring Doctors Comparison ({older_month} vs {newest_month})",
            xaxis_title="Referring Physician",
            yaxis_title="Number of Procedures",
            showlegend=True,
            xaxis_tickangle=45,
            height=500
        )
        
        st.plotly_chart(fig_doctors, use_container_width=True)
        
        # Calculate changes for all doctors
        all_doctors_comparison = pd.DataFrame({
            older_month: older_month_data.groupby('REFERRING PHYSICIAN').size(),
            newest_month: newest_month_data.groupby('REFERRING PHYSICIAN').size()
        }).fillna(0)
        
        # Calculate absolute change
        all_doctors_comparison['Change'] = all_doctors_comparison[newest_month] - all_doctors_comparison[older_month]
        
        # Get top 10 gainers and losers
        gainers = all_doctors_comparison.nlargest(10, 'Change')
        losers = all_doctors_comparison.nsmallest(10, 'Change')
        
        # Display gainers and losers
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 Gainers")
            fig_gainers = pl.graph_objects.Figure(data=[
                pl.graph_objects.Bar(
                    x=gainers.index,
                    y=gainers['Change'],
                    text=gainers['Change'].round(0).astype(int),
                    textposition='auto',
                    marker_color=COLOR_SCHEME[0]
                )
            ])
            fig_gainers.update_layout(
                title=f"Largest Increases ({older_month} to {newest_month})",
                yaxis_title="Additional Procedures",
                xaxis_tickangle=45
            )
            st.plotly_chart(fig_gainers, use_container_width=True)
        
        with col2:
            st.subheader("Top 10 Decreases")
            fig_losers = pl.graph_objects.Figure(data=[
                pl.graph_objects.Bar(
                    x=losers.index,
                    y=losers['Change'],
                    text=losers['Change'].round(0).astype(int),
                    textposition='auto',
                    marker_color=COLOR_SCHEME[1]
                )
            ])
            fig_losers.update_layout(
                title=f"Largest Decreases ({older_month} to {newest_month})",
                yaxis_title="Change in Procedures",
                xaxis_tickangle=45
            )
            st.plotly_chart(fig_losers, use_container_width=True)
        
        # Top 10 insurances comparison
        st.subheader("Top 10 Insurances")
        insurance_counts = {}
        for month in compare_months:
            month_data = compare_data[compare_data['Month'] == month]
            insurance_counts[month] = month_data.groupby('Data Set').size().nlargest(10)
        
        # Create comparison bar chart
        insurance_comparison = pd.DataFrame({
            compare_months[0]: insurance_counts[compare_months[0]],
            compare_months[1]: insurance_counts[compare_months[1]]
        }).fillna(0)
        
        fig_insurance = pl.graph_objects.Figure(data=[
            pl.graph_objects.Bar(
                name=compare_months[0], 
                x=insurance_comparison.index, 
                y=insurance_comparison[compare_months[0]], 
                marker_color=COLOR_SCHEME[0]
            ),
            pl.graph_objects.Bar(
                name=compare_months[1], 
                x=insurance_comparison.index, 
                y=insurance_comparison[compare_months[1]], 
                marker_color=COLOR_SCHEME[1]
            )
        ])
        fig_insurance.update_layout(
            barmode='group',
            title="Top 10 Insurances Comparison",
            xaxis_title="Insurance",
            yaxis_title="Number of Procedures"
        )
        st.plotly_chart(fig_insurance, use_container_width=True)

with tab3:
    if top_200_docs is not None:
        st.subheader("Top 200 Doctors Performance and Comparison")
        
        # Add instructions
        st.info("""
        📊 **How to use this tab:**
        - Select one month for individual analysis
        - Select two months for comparison analysis
        - When comparing two months, the first selected month will be the base month, and the second month will show the changes relative to the base month
        """)
        
        # Doctor selector and month filter
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_doctor = st.selectbox(
                "Select Doctor",
                options=top_200_docs['Referring Physician'].tolist()
            )
        with col2:
            compare_months = st.multiselect(
                "Select Month(s) to Analyze (Max 2)",
                options=working_data['Month'].unique(),
                default=[working_data['Month'].unique()[-1]],  # Default to latest month
                max_selections=2,
                help="First month selected will be the base month for comparison"
            )
        
        if len(compare_months) > 0:
            # Filter data for selected doctor and months
            doctor_data = working_data[
                (working_data['REFERRING PHYSICIAN'] == selected_doctor) &
                (working_data['Month'].isin(compare_months))
            ]
            
            if len(compare_months) == 1:
                # Single month analysis
                month_data = doctor_data[doctor_data['Month'] == compare_months[0]]
                
                # Summary metrics in columns
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_referrals = len(month_data)
                    st.metric("Total Procedures", total_referrals)
                with col2:
                    unique_procedures = month_data['PROCEDURE'].nunique()
                    st.metric("Unique Procedures", unique_procedures)
                with col3:
                    unique_insurances = month_data['Data Set'].nunique()
                    st.metric("Unique Insurances", unique_insurances)
                
                # Pie charts for composition
                col1, col2 = st.columns(2)
                
                with col1:
                    # Procedure composition pie chart
                    procedure_comp = month_data['PROCEDURE'].value_counts().reset_index()
                    procedure_comp.columns = ['PROCEDURE', 'Count']
                    
                    fig_procedures = px.pie(
                        procedure_comp,
                        values='Count',
                        names='PROCEDURE',
                        title=f"Procedure Distribution - {selected_doctor} ({compare_months[0]})",
                        color_discrete_sequence=COLOR_SCHEME
                    )
                    st.plotly_chart(fig_procedures, use_container_width=True)
                
                with col2:
                    # Insurance composition pie chart
                    insurance_comp = month_data['Data Set'].value_counts().reset_index()
                    insurance_comp.columns = ['Insurance', 'Count']
                    
                    fig_insurance = px.pie(
                        insurance_comp,
                        values='Count',
                        names='Insurance',
                        title=f"Insurance Distribution - {selected_doctor} ({compare_months[0]})",
                        color_discrete_sequence=COLOR_SCHEME
                    )
                    st.plotly_chart(fig_insurance, use_container_width=True)
                
            else:  # Two month comparison
                newest_month = compare_months[1]
                older_month = compare_months[0]
                
                # Calculate metrics for both months
                metrics = {}
                for month in compare_months:
                    month_data = doctor_data[doctor_data['Month'] == month]
                    metrics[month] = {
                        'Total Procedures': len(month_data),
                        'Unique Procedures': month_data['PROCEDURE'].nunique(),
                        'Unique Insurances': month_data['Data Set'].nunique()
                    }
                
                # Display metrics with month-over-month comparison
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Total Procedures",
                        metrics[newest_month]['Total Procedures'],
                        metrics[newest_month]['Total Procedures'] - metrics[older_month]['Total Procedures']
                    )
                with col2:
                    st.metric(
                        "Unique Procedures",
                        metrics[newest_month]['Unique Procedures'],
                        metrics[newest_month]['Unique Procedures'] - metrics[older_month]['Unique Procedures']
                    )
                with col3:
                    st.metric(
                        "Unique Insurances",
                        metrics[newest_month]['Unique Insurances'],
                        metrics[newest_month]['Unique Insurances'] - metrics[older_month]['Unique Insurances']
                    )
                
                # Create comparison bar charts
                st.subheader(f"Monthly Comparison - {selected_doctor}")
                
                # Procedures by type comparison
                procedures_comp = pd.DataFrame({
                    older_month: doctor_data[doctor_data['Month'] == older_month]['PROCEDURE'].value_counts(),
                    newest_month: doctor_data[doctor_data['Month'] == newest_month]['PROCEDURE'].value_counts()
                }).fillna(0)
                
                fig_procedures = pl.graph_objects.Figure(data=[
                    pl.graph_objects.Bar(
                        name=older_month, 
                        x=procedures_comp.index, 
                        y=procedures_comp[older_month], 
                        marker_color=COLOR_SCHEME[0]
                    ),
                    pl.graph_objects.Bar(
                        name=newest_month, 
                        x=procedures_comp.index, 
                        y=procedures_comp[newest_month], 
                        marker_color=COLOR_SCHEME[1]
                    )
                ])
                fig_procedures.update_layout(
                    barmode='group',
                    title="Procedures Comparison",
                    xaxis_title="Procedure Type",
                    yaxis_title="Number of Procedures"
                )
                st.plotly_chart(fig_procedures, use_container_width=True)
                
                # Insurance comparison
                insurance_comp = pd.DataFrame({
                    older_month: doctor_data[doctor_data['Month'] == older_month]['Data Set'].value_counts(),
                    newest_month: doctor_data[doctor_data['Month'] == newest_month]['Data Set'].value_counts()
                }).fillna(0)
                
                fig_insurance = pl.graph_objects.Figure(data=[
                    pl.graph_objects.Bar(
                        name=older_month, 
                        x=insurance_comp.index, 
                        y=insurance_comp[older_month], 
                        marker_color=COLOR_SCHEME[0]
                    ),
                    pl.graph_objects.Bar(
                        name=newest_month, 
                        x=insurance_comp.index, 
                        y=insurance_comp[newest_month], 
                        marker_color=COLOR_SCHEME[1]
                    )
                ])
                fig_insurance.update_layout(
                    barmode='group',
                    title="Insurance Distribution Comparison",
                    xaxis_title="Insurance",
                    yaxis_title="Number of Procedures"
                )
                st.plotly_chart(fig_insurance, use_container_width=True)
                
                # Add pie charts for newest month composition
                st.subheader(f"Current Month Composition ({newest_month})")
                col1, col2 = st.columns(2)
                
                newest_month_data = doctor_data[doctor_data['Month'] == newest_month]
                
                with col1:
                    # Procedure composition pie chart
                    procedure_comp = newest_month_data['PROCEDURE'].value_counts().reset_index()
                    procedure_comp.columns = ['PROCEDURE', 'Count']
                    
                    fig_procedures_pie = px.pie(
                        procedure_comp,
                        values='Count',
                        names='PROCEDURE',
                        title=f"Current Procedure Distribution - {selected_doctor}",
                        color_discrete_sequence=COLOR_SCHEME
                    )
                    st.plotly_chart(fig_procedures_pie, use_container_width=True)
                
                with col2:
                    # Insurance composition pie chart
                    insurance_comp = newest_month_data['Data Set'].value_counts().reset_index()
                    insurance_comp.columns = ['Insurance', 'Count']
                    
                    fig_insurance_pie = px.pie(
                        insurance_comp,
                        values='Count',
                        names='Insurance',
                        title=f"Current Insurance Distribution - {selected_doctor}",
                        color_discrete_sequence=COLOR_SCHEME
                    )
                    st.plotly_chart(fig_insurance_pie, use_container_width=True)
        
        else:
            st.warning("Please select at least one month to analyze")
    else:
        st.error("Please ensure the Top 200 Doctores.xlsx file is in the same directory as the app")

with tab4:
    st.subheader("Top 200 Doctors Representative Analysis")
    
    # Add instructions
    st.info("""
    📊 **Representative Categories:**
    - **Alex**: Doctors assigned to Alex
    - **Luis**: Doctors assigned to Luis  
    - **Gerardo**: Doctors assigned to Gerardo
    """)
    
    # Month selector
    compare_months = st.multiselect(
        "Select Two Months to Compare",
        options=working_data['Month'].unique(),
        default=working_data['Month'].unique()[-2:],  # Default to last two months
        max_selections=2,
        help="First month selected will be the base month for comparison"
    )
    
    if len(compare_months) == 2:
        older_month, newest_month = compare_months
        
        # Get the correct column name
        responsible_column = top_200_docs['correct_responsible_column'].iloc[0]
        
        # Categorize doctors by representative
        alex_docs = top_200_docs[
            top_200_docs[responsible_column] == 'ALEX'
        ]['Referring Physician'].tolist()
        
        luis_docs = top_200_docs[
            top_200_docs[responsible_column] == 'LUIS'
        ]['Referring Physician'].tolist()
        
        gerardo_docs = top_200_docs[
            top_200_docs[responsible_column] == 'GERARDO'
        ]['Referring Physician'].tolist()
        
        # Calculate metrics for each category
        categories = {
            'Alex': alex_docs,
            'Luis': luis_docs,
            'Gerardo': gerardo_docs
        }
        
        # Display category sizes and total referrals
        st.subheader("Number of Doctors Assigned to Each Representative")
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        for i, (category, doctors) in enumerate(categories.items()):
            with cols[i]:
                st.metric(f"{category}", len(doctors))
        
        # Calculate and display total referrals per category
        st.subheader("Total Referrals by Doctors Assigned")
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for i, (category, doctors) in enumerate(categories.items()):
            with cols[i]:
                # Get referrals for both months
                old_referrals = len(working_data[
                    (working_data['Month'] == older_month) & 
                    (working_data['REFERRING PHYSICIAN'].isin(doctors))
                ])
                
                new_referrals = len(working_data[
                    (working_data['Month'] == newest_month) & 
                    (working_data['REFERRING PHYSICIAN'].isin(doctors))
                ])
                
                # Calculate the difference
                difference = new_referrals - old_referrals
                
                # Display metric with delta
                st.metric(
                    f"Referrals ({newest_month})",
                    new_referrals,
                    delta=difference,
                    delta_color="normal"
                )
        
        # Calculate performance metrics for each category and month
        performance_data = []
        for category, doctors in categories.items():
            for month in compare_months:
                month_data = working_data[
                    (working_data['Month'] == month) & 
                    (working_data['REFERRING PHYSICIAN'].isin(doctors))
                ]
                
                performance_data.append({
                    'Category': category,
                    'Month': month,
                    'Total Procedures': len(month_data),
                    'Unique Doctors Active': month_data['REFERRING PHYSICIAN'].nunique(),
                    'Avg Procedures per Doctor': len(month_data) / len(doctors) if len(doctors) > 0 else 0,
                    'Unique Insurances': month_data['Data Set'].nunique(),
                })
        
        performance_df = pd.DataFrame(performance_data)
        
        # Create visualization for key metrics
        st.subheader("Category Performance Comparison")
        
        # Total Procedures by Category
        fig_procedures = pl.graph_objects.Figure()
        for i, (category, doctors) in enumerate(categories.items()):
            category_data = performance_df[performance_df['Category'] == category]
            fig_procedures.add_trace(pl.graph_objects.Bar(
                name=category,
                x=category_data['Month'],
                y=category_data['Total Procedures'],
                text=category_data['Total Procedures'],
                textposition='auto',
                marker_color=COLOR_SCHEME[i % len(COLOR_SCHEME)]
            ))
        
        fig_procedures.update_layout(
            title="Total Procedures by Category",
            barmode='group',
            yaxis_title="Number of Procedures"
        )
        st.plotly_chart(fig_procedures, use_container_width=True)
        
        # Average Procedures per Doctor
        fig_avg = pl.graph_objects.Figure()
        for i, (category, doctors) in enumerate(categories.items()):
            category_data = performance_df[performance_df['Category'] == category]
            fig_avg.add_trace(pl.graph_objects.Bar(
                name=category,
                x=category_data['Month'],
                y=category_data['Avg Procedures per Doctor'],
                text=category_data['Avg Procedures per Doctor'].round(1),
                textposition='auto',
                marker_color=COLOR_SCHEME[i % len(COLOR_SCHEME)]
            ))
        
        fig_avg.update_layout(
            title="Average Procedures per Doctor",
            barmode='group',
            yaxis_title="Average Procedures"
        )
        st.plotly_chart(fig_avg, use_container_width=True)
        
        # Active Doctors
        fig_active = pl.graph_objects.Figure()
        for i, (category, doctors) in enumerate(categories.items()):
            category_data = performance_df[performance_df['Category'] == category]
            fig_active.add_trace(pl.graph_objects.Bar(
                name=category,
                x=category_data['Month'],
                y=category_data['Unique Doctors Active'],
                text=category_data['Unique Doctors Active'],
                textposition='auto',
                marker_color=COLOR_SCHEME[i % len(COLOR_SCHEME)]
            ))
        
        fig_active.update_layout(
            title="Active Doctors by Category",
            barmode='group',
            yaxis_title="Number of Active Doctors"
        )
        st.plotly_chart(fig_active, use_container_width=True)
        
        # Summary table
        st.subheader("Detailed Performance Metrics")
        summary_table = performance_df.pivot(
            index='Category',
            columns='Month',
            values=['Total Procedures', 'Unique Doctors Active', 'Avg Procedures per Doctor']
        ).round(2)
        st.dataframe(summary_table)
    
    else:
        st.warning("Please select exactly two months for comparison")

# Add this function after imports
def add_back_to_top():
    js = '''
    <script>
        var mybutton = document.createElement("button");
        mybutton.innerHTML = "↑ Back to Top";
        mybutton.style.position = "fixed";
        mybutton.style.bottom = "20px";
        mybutton.style.right = "30px";
        mybutton.style.zIndex = "99";
        mybutton.style.border = "none";
        mybutton.style.outline = "none";
        mybutton.style.backgroundColor = "#0E1117";
        mybutton.style.color = "white";
        mybutton.style.cursor = "pointer";
        mybutton.style.padding = "15px";
        mybutton.style.borderRadius = "4px";
        mybutton.style.fontSize = "18px";

        // When scrolling down 20px, show the button
        window.onscroll = function() {scrollFunction()};

        function scrollFunction() {
            if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
                mybutton.style.display = "block";
            } else {
                mybutton.style.display = "none";
            }
        }

        // Add click event
        mybutton.addEventListener("click", function() {
            document.body.scrollTop = 0; // For Safari
            document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
        });

        document.body.appendChild(mybutton);
    </script>
    '''
    st.components.v1.html(js, height=0)

# Add this at the end of your main code
add_back_to_top()
