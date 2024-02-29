import pandas as pd
import numpy as np

def analyze_demand(data):
    # Step 1: Organize Data
    quarters = ["FY20 Q4", "FY21 Q1", "FY21 Q2", "FY21 Q3", "FY21 Q4", 
                "FY22 Q1", "FY22 Q2", "FY22 Q3", "FY22 Q4", 
                "FY23 Q1", "FY23 Q2", "FY23 Q3"]
    df = pd.DataFrame(data, index=quarters, columns=["Demand"])
    
    # Step 2: Analyze Quarterly Demand
    df['Fiscal Quarter'] = [q.split(" ")[1] for q in quarters]
    average_demand_per_quarter = df.groupby('Fiscal Quarter').mean()
    std_deviation_per_quarter = df.groupby('Fiscal Quarter').std()
    
    # Step 3: Identify Bias
    # Bias identification would be more subjective based on std_deviation_per_quarter and external knowledge
    
    # Step 4: Yearly Trend Analysis
    fy_demand = {
        "FY20": df.loc["FY20 Q4", "Demand"],
        "FY21": df.loc["FY21 Q1":"FY21 Q4", "Demand"].sum(),
        "FY22": df.loc["FY22 Q1":"FY22 Q4", "Demand"].sum(),
        "FY23": df.loc["FY23 Q1":"FY23 Q3", "Demand"].sum(),
    }
    fy_demand = pd.Series(fy_demand)
    yoy_growth = fy_demand.pct_change()
    
    # Step 5: Predict FY23 Q4 Demand
    adjusted_fy23_demand = fy_demand["FY23"] / (3/4)  # Assuming Q1-Q3 represents 75% of the year
    predicted_fy23_q4_demand = adjusted_fy23_demand - fy_demand["FY23"]
    
    return {
        "Average Demand Per Quarter": average_demand_per_quarter,
        "Standard Deviation Per Quarter": std_deviation_per_quarter,
        "FY Demand Totals": fy_demand,
        "YoY Growth": yoy_growth,
        "Predicted FY23 Q4 Demand": predicted_fy23_q4_demand,
    }
def analyze_demand_from_string(input_string):
    # Convert space-separated string to list of integers
    data = [int(value) for value in input_string.split()]
    
    # Perform the generalized analysis
    return analyze_demand(data)

# Sample input string, space-separated
input_string = "28279	22704	24098	31461	47009	35145	45978	34518	40605	26925	23635	17795"
result_from_string = analyze_demand_from_string(input_string)

# Display the results
print(result_from_string)
