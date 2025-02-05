import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import re
import seaborn as sns
from datetime import datetime
from collections import defaultdict

# GRAPH_FOLDER = "static/graphs"
# os.makedirs(GRAPH_FOLDER, exist_ok=True)

GRAPH_FOLDER = os.path.join(os.path.dirname(__file__), "static/graphs")
os.makedirs(GRAPH_FOLDER, exist_ok=True)

def analyze_transactions(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": "Invalid file format"}, None

    sms_list = data.get("sms", [])
    transactions = []
    
    for message in sms_list:
        try:
            body = message.get("body", "")
            if "ETB" not in body:
                continue

            # Extract amount
            amount_part = body.split("ETB")[1].strip()
            amount_text = re.findall(r"[\d,]+\.?\d*", amount_part)[0]
            amount_cleaned = amount_text.replace(',', '')
            
            # Handle multiple decimals
            if amount_cleaned.count('.') > 1:
                parts = amount_cleaned.split('.')
                amount_cleaned = f"{parts[0]}.{''.join(parts[1:])}"
                
            # Date handling
            date_ms = int(message.get("date", 0))
            transaction_date = datetime.fromtimestamp(date_ms / 1000)
            
            transactions.append({
                "date": transaction_date,
                "amount": float(amount_cleaned)
            })
            
        except (IndexError, ValueError, KeyError) as e:
            continue

    if not transactions:
        return {"error": "No valid transactions found"}, None

    df = pd.DataFrame(transactions)
    
    # Calculate statistics
    stats = {
        "total_spent": df['amount'].sum(),
        "daily_average": df['amount'].sum() / df['date'].nunique(),
        "largest_transaction": df['amount'].max(),
        "most_active_day": df['date'].dt.day_name().mode()[0],
        "transactions_per_day": len(df) / df['date'].nunique(),
        "top_merchant": get_top_merchant(sms_list),
        "peak_hour": df['date'].dt.hour.mode()[0],
        "biggest_spending_day": df.groupby(df['date'].dt.date)['amount'].sum().idxmax().strftime("%Y-%m-%d"),
        "savings_opportunity": calculate_savings(df)
    }

    # Generate graphs
    graph_filenames = {
        "monthly": create_monthly_chart(df),
        "distribution": create_donut_chart(df),
        "heatmap": create_heatmap(df)
    }
    
    return stats, graph_filenames

def create_monthly_chart(df):
    plt.style.use('seaborn-v0_8')  # Correct seaborn style
    fig, ax = plt.subplots(figsize=(12, 6))
    
    monthly = df.groupby(pd.PeriodIndex(df['date'], freq="M"))['amount'].sum()
    monthly.plot(kind='bar', color='#00FF88', ax=ax)
    
    ax.set_title('Monthly Spending Pattern', fontsize=14, pad=20)
    ax.set_xlabel('')
    ax.set_ylabel('Amount (ETB)', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.spines[['top','right']].set_visible(False)
    
    # Add value labels
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.0f}", 
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', 
                    xytext=(0, 5), 
                    textcoords='offset points')
    
    filename = "monthly_chart.png"
    plt.savefig(os.path.join(GRAPH_FOLDER, filename), bbox_inches='tight', dpi=300)
    plt.close()
    return filename

def create_donut_chart(df):
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(8, 8))
    
    amounts = pd.cut(df['amount'], 
                    bins=[0, 100, 500, 1000, 5000, float('inf')],
                    labels=['Micro (<100)', 'Small (100-500)', 'Medium (500-1000)', 
                           'Large (1000-5000)', 'XL (>5000)'])
    counts = amounts.value_counts()
    
    colors = ['#00FF88', '#00E676', '#00C853', '#009624', '#006400']
    wedges, texts, autotexts = ax.pie(counts, colors=colors, startangle=90,
                                     wedgeprops=dict(width=0.4), autopct='%1.1f%%')
    
    # Add center circle
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    ax.add_artist(centre_circle)
    
    ax.set_title('Transaction Size Distribution', fontsize=14, pad=20)
    plt.legend(wedges, counts.index,
              title="Categories",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))
    
    filename = "donut_chart.png"
    plt.savefig(os.path.join(GRAPH_FOLDER, filename), bbox_inches='tight', dpi=300)
    plt.close()
    return filename

def create_heatmap(df):
    df['day'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    heatmap_data = df.pivot_table(index='day', columns='hour', values='amount', aggfunc='count', fill_value=0)
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(days_order)
    
    plt.figure(figsize=(14, 6))
    sns.heatmap(heatmap_data, cmap='Greens', linewidths=0.5)
    plt.title('Transaction Frequency Heatmap', fontsize=14, pad=20)
    plt.xlabel('Hour of Day')
    plt.ylabel('')
    
    filename = "heatmap.png"
    plt.savefig(os.path.join(GRAPH_FOLDER, filename), bbox_inches='tight', dpi=300)
    plt.close()
    return filename

def get_top_merchant(sms_list):
    merchant_counts = defaultdict(int)
    pattern = r"ETB\s[\d,]+\.?\d*\s(?:to|at|for)\s([A-Za-z0-9\s]+)"
    
    for msg in sms_list:
        match = re.search(pattern, msg.get('body', ''))
        if match:
            merchant = match.group(1).strip()
            merchant_counts[merchant] += 1
            
    if merchant_counts:
        return max(merchant_counts, key=merchant_counts.get)
    return "N/A"

def calculate_savings(df):
    small_trans = df[df['amount'] < 500]
    return {
        'daily_coffee_cost': small_trans.groupby(small_trans['date'].dt.date)['amount'].sum().mean(),
        'potential_yearly_savings': small_trans['amount'].sum() * 0.3  # Assume 30% savings
    }
