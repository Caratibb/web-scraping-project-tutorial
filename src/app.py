import os
from bs4 import BeautifulSoup
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, MetaData, Table, Column, Float, String
from dotenv import load_dotenv

url = 'https://ycharts.com/companies/TSLA/revenues'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    with open('downloaded_page.html', 'w', encoding='utf-8') as file:
        file.write(response.text)
    print("HTML page downloaded successfully.")
else:
    print(f"Failed to retrieve page. Status code: {response.status_code}")

# Load the HTML content from the file
with open('downloaded_page.html', 'r', encoding='utf-8') as file:
    html_content = file.read()

# Parse the HTML with BeautifulSoup
soup = BeautifulSoup(html_content, 'lxml')

# Find all tables in the page
tables = soup.find_all('table')

# Initialize the variable to store the quarterly table
quarterly_table = None

# Identify the table with quarterly evolution
for table in tables:
    if 'Quarter' in table.get_text():  # Look for the 'Quarter' keyword in the table
        quarterly_table = table
        break

# Check if the table was found
if quarterly_table:
    # Extract headers from the first row
    first_row = quarterly_table.find_all('tr')[0]
    headers = [header.text.strip() for header in first_row.find_all('td')]

    # Extract rows
    rows = []
    for row in quarterly_table.find_all('tr')[1:]:  # Skip the header row
        cells = row.find_all('td')
        row_data = [cell.text.strip() for cell in cells]
        rows.append(row_data)

    # Print headers and rows to debug
    print("Headers:", headers)
    print("Rows:", rows)

    # Store the data in a DataFrame
    try:
        # Ensure all rows have the same number of columns as headers
        max_columns = len(headers)
        cleaned_rows = [row[:max_columns] for row in rows]  # Trim rows to match header length
        df = pd.DataFrame(cleaned_rows, columns=headers)

        # Display the DataFrame
        print(df)
    except Exception as e:
        print("Error creating DataFrame:", e)
else:
    print("Quarterly table not found.")

# Function to clean up the monetary values
def clean_value(value):
    if value:
        # Remove dollar signs, commas, and strip whitespace
        value = value.replace('$', '').replace(',', '').strip()
        # Convert to float if possible, otherwise keep as is
        return float(value) if value else None
    return None

# Apply the cleaning function to each cell in the DataFrame
df = df.applymap(clean_value)

# Drop rows that have all elements as None (no information)
df.dropna(how='all', inplace=True)

# Drop columns that are empty or irrelevant
df.dropna(axis=1, how='all', inplace=True)

# Reset the index after dropping rows
df.reset_index(drop=True, inplace=True)

# Display the cleaned DataFrame
print(df)

# Load the .env file variables if needed
load_dotenv()

# Define your database connection using SQLAlchemy
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://user:password@localhost/my_clean_database'
engine = create_engine(DATABASE_URL)

# Create a connection to the database
with engine.connect() as connection:
    metadata = MetaData()

    # Define the table structure
    clean_data_table = Table(
        'clean_data', metadata,
        Column('Quarter', String, primary_key=True),
        Column('Revenue', Float)
    )

    # Create the table in the database
    metadata.create_all(engine)

    # Insert the cleaned data into the table
    for index, row in df.iterrows():
        insert_stmt = clean_data_table.insert().values(
            Quarter=row['Quarter'],
            Revenue=row['Revenue']
        )
        connection.execute(insert_stmt)

    # Print confirmation
    print("Data inserted successfully into the clean_data table.")

# Line Plot: Revenue Over Time
plt.figure(figsize=(10, 6))
sns.lineplot(data=df, x='Quarter', y='Revenue', marker='o')
plt.title('Quarterly Revenue Over Time')
plt.xlabel('Quarter')
plt.ylabel('Revenue ($)')
plt.xticks(rotation=45)
plt.grid(True)
plt.show()

# Bar Plot: Revenue Per Quarter
plt.figure(figsize=(10, 6))
sns.barplot(data=df, x='Quarter', y='Revenue', palette='viridis')
plt.title('Quarterly Revenue Comparison')
plt.xlabel('Quarter')
plt.ylabel('Revenue ($)')
plt.xticks(rotation=45)
plt.show()

# Calculate percentage change for heatmap
df['Revenue_Change'] = df['Revenue'].pct_change() * 100
plt.figure(figsize=(10, 6))
sns.heatmap(df[['Revenue_Change']].T, cmap='coolwarm', annot=True, fmt='.2f')
plt.title('Revenue Growth Percentage Change')
plt.xlabel('Quarter')
plt.ylabel('Growth (%)')
plt.xticks(rotation=45)
plt.show()