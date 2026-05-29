import pandas as pd
import numpy as np
import uuid
import random
from datetime import datetime, timedelta

def generate_data():
    np.random.seed(42)
    random.seed(42)
    
    start_date = datetime(2025, 1, 13)
    end_date = datetime(2026, 1, 12)
    delta_days = (end_date - start_date).days
    
    accounts = ['ACC-STUDENT-001', 'ACC-STUDENT-002', 'ACC-STUDENT-003', 'ACC-STUDENT-004', 'ACC-STUDENT-005']
    
    transactions = []
    
    # Template helpers
    merchants = {
        'Food': ['Canteen', 'Cafe', 'Restaurant', 'Bakery', 'Local Eatery', 'Burger House', 'Boba Shop'],
        'Transport': ['Bus', 'Pathao', 'Local Taxi', 'Sajha Yatayat', 'InDrive', 'Microbus'],
        'Shopping': ['Mall', 'Local Store', 'Clothing Shop', 'Miniso', 'Daraz', 'Bhatbhateni Fashion'],
        'Groceries': ['Bhatbhateni', 'Big Mart', 'Saleways', 'Local Grocery', 'Fresh Vegetable Vendor'],
        'Coffee': ['Himalayan Java', 'Red Mug Cafe', 'Beans Cafe', 'Local Tea Stall', 'Coffee Point'],
        'Entertainment': ['QFX Cinemas', 'One Cinemas', 'Fuzz Factory', 'Netflix', 'Spotify', 'Gaming Zone'],
        'Utilities': ['Rent House Ltd', 'Worldlink', 'Nepal Electricity Authority', 'Kathmandu Upatyaka Khanepani'],
        'Travel': ['Yeti Airlines', 'Sajha Yatayat Deluxe', 'Tourist Bus', 'Resort Pokhara', 'Hotel Chitwan'],
        'Income': ['Freelance Work', 'Family Transfer', 'Part-time Gig', 'Scholarship', 'Tutoring']
    }
    
    descriptions = {
        'Food': ['Meals', 'Lunch', 'Dinner', 'Snacks', 'Burger & Fries', 'Coke and Momo', 'Breakfast'],
        'Transport': ['Daily Commute', 'Ride Sharing', 'Taxi Ride', 'Micro Fare', 'Bus Ticket'],
        'Shopping': ['Shopping', 'New Shoes', 'T-shirt', 'Gift for Mom', 'Birthday Gift', 'Saree for Mother', 'Books'],
        'Groceries': ['Weekly Groceries', 'Vegetables & Fruits', 'Rice and Oil', 'Monthly Supplies', 'Dairy Products'],
        'Coffee': ['Americano', 'Latte', 'Chiya', 'Iced Coffee', 'Cappuccino'],
        'Entertainment': ['Movie Ticket', 'Popcorn & Soda', 'Netflix Subscription', 'Spotify Premium', 'Bowling Session'],
        'Utilities': ['House Rent', 'WiFi Internet', 'Electricity Bill', 'Water Bill'],
        'Travel': ['Pokhara Trip', 'Bus to Chitwan', 'Weekend Getaway', 'Hotel Stay'],
        'Income': ['Part-time Payment', 'Monthly Allowance', 'Freelance Project', 'Scholarship payout', 'Tutoring fee']
    }

    for account in accounts:
        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.weekday() # 0 = Monday, 6 = Sunday
            day_of_month = current_date.day
            
            # --- 1. INCOME ---
            # Allowance/Salary at start of month
            if day_of_month == 1:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=9, minute=0).isoformat() + 'Z',
                    'amount': round(random.uniform(25000, 35000), 2),
                    'currency': 'NPR',
                    'type': 'CREDIT',
                    'status': 'COMPLETED',
                    'description': 'Monthly Allowance',
                    'merchant': 'Family Transfer',
                    'category': 'Income'
                })
            
            # Occasional freelance income (1-2 times a month)
            if day_of_month in [10, 24] and random.random() < 0.6:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=14, minute=30).isoformat() + 'Z',
                    'amount': round(random.uniform(3000, 8000), 2),
                    'currency': 'NPR',
                    'type': 'CREDIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Income']),
                    'merchant': random.choice(merchants['Income']),
                    'category': 'Income'
                })

            # --- 2. UTILITIES ---
            # Rent and Internet once a month
            if day_of_month == 2:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=10, minute=0).isoformat() + 'Z',
                    'amount': round(random.uniform(8000, 14000), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': 'House Rent',
                    'merchant': 'Rent House Ltd',
                    'category': 'Utilities'
                })
            if day_of_month == 5:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=11, minute=15).isoformat() + 'Z',
                    'amount': round(random.uniform(1200, 2500), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': 'WiFi Internet',
                    'merchant': 'Worldlink',
                    'category': 'Utilities'
                })

            # --- 3. GROCERIES ---
            # Weekly grocery shopping on weekends (Saturday/Sunday)
            if day_of_week in [5, 6] and random.random() < 0.8:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=12, minute=0).isoformat() + 'Z',
                    'amount': round(random.uniform(1500, 4500), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Groceries']),
                    'merchant': random.choice(merchants['Groceries']),
                    'category': 'Groceries'
                })

            # --- 4. ENTERTAINMENT ---
            # Movies/Netflix on Sunday
            if day_of_week == 6 and random.random() < 0.5:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=18, minute=30).isoformat() + 'Z',
                    'amount': round(random.uniform(350, 1200), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Entertainment']),
                    'merchant': random.choice(merchants['Entertainment']),
                    'category': 'Entertainment'
                })
            # Monthly streaming cost
            if day_of_month == 15:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=8, minute=0).isoformat() + 'Z',
                    'amount': round(random.uniform(250, 500), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': 'Spotify Premium',
                    'merchant': 'Spotify',
                    'category': 'Entertainment'
                })

            # --- 5. COFFEE ---
            # Frequent coffee on weekdays
            if day_of_week < 5 and random.random() < 0.6:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=8, minute=30).isoformat() + 'Z',
                    'amount': round(random.uniform(100, 350), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Coffee']),
                    'merchant': random.choice(merchants['Coffee']),
                    'category': 'Coffee'
                })

            # --- 6. FOOD ---
            # Daily meals/canteen/restaurant
            food_count = random.randint(1, 2) if day_of_week < 5 else random.randint(0, 2)
            for _ in range(food_count):
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=random.choice([12, 13, 19, 20]), minute=random.randint(0, 59)).isoformat() + 'Z',
                    'amount': round(random.uniform(150, 800), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Food']),
                    'merchant': random.choice(merchants['Food']),
                    'category': 'Food'
                })

            # --- 7. TRANSPORT ---
            # Commutes (Bus, Pathao, Taxi)
            trans_count = random.randint(1, 2) if day_of_week < 5 else random.randint(0, 1)
            for _ in range(trans_count):
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=random.choice([9, 17, 18]), minute=random.randint(0, 59)).isoformat() + 'Z',
                    'amount': round(random.uniform(50, 500), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Transport']),
                    'merchant': random.choice(merchants['Transport']),
                    'category': 'Transport'
                })

            # --- 8. SHOPPING (including gifts for mom/family) ---
            # Occasional shopping (every 2-3 weeks)
            if random.random() < 0.08:
                is_gift = random.random() < 0.35
                desc = "Gift for Mom" if is_gift else random.choice(descriptions['Shopping'])
                amt = round(random.uniform(1500, 6000), 2)
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=16, minute=20).isoformat() + 'Z',
                    'amount': amt,
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': desc,
                    'merchant': random.choice(merchants['Shopping']),
                    'category': 'Shopping'
                })

            # --- 9. TRAVEL ---
            # Occasional travel (every 2 months)
            if random.random() < 0.015:
                transactions.append({
                    'transaction_id': str(uuid.uuid4()),
                    'account_id': account,
                    'date': current_date.replace(hour=7, minute=0).isoformat() + 'Z',
                    'amount': round(random.uniform(3000, 10000), 2),
                    'currency': 'NPR',
                    'type': 'DEBIT',
                    'status': 'COMPLETED',
                    'description': random.choice(descriptions['Travel']),
                    'merchant': random.choice(merchants['Travel']),
                    'category': 'Travel'
                })

            current_date += timedelta(days=1)

    # --- NOISE GENERATION ---
    df = pd.DataFrame(transactions)
    print(f"Generated {len(df)} clean records. Now applying noise...")
    
    # 1. Inconsistent Date Formats (e.g. drop Z, replace T with space, use slashes)
    mask_date_noisy = np.random.rand(len(df)) < 0.04
    df.loc[mask_date_noisy, 'date'] = df.loc[mask_date_noisy, 'date'].apply(
        lambda d: d.replace('T', ' ').replace('Z', '') if random.random() < 0.5 else datetime.fromisoformat(d.replace('Z', '+00:00')).strftime('%Y/%m/%d')
    )
    
    # 2. Inconsistent Category Casing (e.g. food, FOOD, groceries, coffee)
    mask_cat_noisy = np.random.rand(len(df)) < 0.05
    df.loc[mask_cat_noisy, 'category'] = df.loc[mask_cat_noisy, 'category'].apply(
        lambda c: c.lower() if random.random() < 0.5 else c.upper()
    )
    
    # 3. Missing descriptions or merchants (NaN)
    mask_desc_nan = np.random.rand(len(df)) < 0.03
    df.loc[mask_desc_nan, 'description'] = None
    
    mask_merch_nan = np.random.rand(len(df)) < 0.03
    df.loc[mask_merch_nan, 'merchant'] = None
    
    # 4. Zero/Negative/Refund amounts
    mask_amount_refund = np.random.rand(len(df)) < 0.015
    df.loc[mask_amount_refund, 'amount'] = df.loc[mask_amount_refund, 'amount'].apply(
        lambda a: -a if random.random() < 0.5 else 0.0
    )
    
    # Cast 'amount' to object type so we can store string-formatted amounts
    df['amount'] = df['amount'].astype(object)

    # 5. String-formatted amounts (e.g. "Rs. 1,200", "500.00")
    mask_amount_str = np.random.rand(len(df)) < 0.02
    df.loc[mask_amount_str, 'amount'] = df.loc[mask_amount_str, 'amount'].apply(
        lambda a: f"Rs. {a:,}" if random.random() < 0.5 else f"{a}"
    )

    # 6. Duplicates
    duplicates = df.sample(frac=0.01, random_state=42)
    df = pd.concat([df, duplicates], ignore_index=True)
    
    # Shuffle to mix duplicates
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    # Write to CSV
    df.to_csv('transactions.csv', index=False)
    print(f"Dataset generated. Total rows (including noise and duplicates): {len(df)}")
    print("Category value counts in raw generated file (pre-standardization):")
    print(df['category'].value_counts())

if __name__ == '__main__':
    generate_data()
