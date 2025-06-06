import pandas as pd
import numpy as np
import os
import json
import logging
import traceback
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import csv
import tempfile
import io
import sys

# Configure logging
logger = logging.getLogger(__name__)

# Get Gemini API key from settings or environment
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))

# Initialize Gemini if API key is available
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        GEMINI_AVAILABLE = True
        logger.info("Gemini API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {e}")
        GEMINI_AVAILABLE = False
else:
    logger.warning("No Gemini API key found. Column mapping will use basic heuristics only.")
    GEMINI_AVAILABLE = False

def clean_dataframe(df):
    """
    Clean the dataframe by normalizing column names and removing duplicate columns
    
    Args:
        df: pandas DataFrame containing the sales data
        
    Returns:
        pandas DataFrame: Cleaned dataframe with normalized column names
    """
    try:
        # Make a copy to avoid modifying the original
        df_clean = df.copy()
        
        # Handle potential issues with column names
        # Replace special characters in column names with underscores
        df_clean.columns = [str(col).strip().replace(' ', '_').replace('\n', '_').replace('-', '_') for col in df_clean.columns]
        
        # Remove duplicate columns if any
        df_clean = df_clean.loc[:, ~df_clean.columns.duplicated()]
        
        # Log the result of the cleaning operation
        logger.info(f"Column names normalized. Original shape: {df.shape}, Result shape: {df_clean.shape}")
        logger.info(f"Normalized columns: {df_clean.columns.tolist()}")
        
        return df_clean
    except Exception as e:
        logger.error(f"Error normalizing column names: {e}")
        # Return original dataframe if cleaning fails
        return df

def identify_columns_with_gemini(df, file_path=None):
    """
    Use Gemini AI ONLY for column identification in the dataset
    
    Args:
        df: pandas DataFrame containing the sales data
        file_path: path to the original file (optional)
        
    Returns:
        dict: Mapping of analysis categories to column names
    """
    # First normalize column names
    df_clean = clean_dataframe(df)
    
    # Initialize empty column mapping with warnings
    column_mapping = {
        "sales_amount": None,
        "order_date": None,
        "product_name": None,
        "customer_location": None,
        "sales_channel": None,
        "product_category": None,
        "order_id": None,
        "customer_id": None,
        "unit_price": None,
        "quantity": None,
        "transaction_type": None,  # Added transaction type field
        "_warnings": []
    }
    
    # If dataset is too small or appears to be a descriptor rather than data, warn the user
    if df.shape[0] < 3 or df.shape[1] < 3:
        column_mapping["_warnings"].append(
            f"This file appears to contain very limited data ({df.shape[0]} rows, {df.shape[1]} columns). " +
            "It may be a report description rather than actual sales data."
        )
        logger.warning(f"Very small dataset or report description detected: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Try to identify if any column appears to contain sales-related text
        for col in df_clean.columns:
            col_str = str(col).lower()
            sample_data = str(" ".join(df_clean[col].dropna().astype(str).tolist())).lower()
            
            # Check for sales-related keywords in column name or data
            if any(keyword in col_str for keyword in ['sales', 'revenue', 'order', 'invoice', 'amount']):
                column_mapping["_warnings"].append(
                    f"Found potential sales-related header '{col}'. This might be a report description column."
                )
            
            # Check if sample data contains sales-related text
            if any(keyword in sample_data for keyword in 
                  ['invoice', 'sales report', 'order', 'transaction', 'revenue', 'flipkart', 'amazon', 'meesho']):
                column_mapping["_warnings"].append(
                    f"Column '{col}' appears to contain report descriptions rather than actual sales data."
                )
        
        # Return early with warnings
        return column_mapping
    
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini AI not available, using heuristic column identification")
        return identify_columns_heuristically(df_clean)
    
    try:
        # Get column names and sample data for the prompt
        column_names = df_clean.columns.tolist()
        logger.info(f"Identifying columns from: {column_names}")
        
        # Prepare sample data including column types to help with identification
        column_types = {}
        column_unique_values = {}
        column_statistics = {}
        
        for col in df_clean.columns:
            try:
                # Check if column is numeric
                if pd.api.types.is_numeric_dtype(df_clean[col]):
                    column_types[col] = "numeric"
                    # Add some statistics for numeric columns
                    column_statistics[col] = {
                        "min": float(df_clean[col].min()),
                        "max": float(df_clean[col].max()),
                        "mean": float(df_clean[col].mean()),
                        "has_decimals": any(x % 1 != 0 for x in df_clean[col].dropna().head(20))
                    }
                # Check if column is datetime
                elif pd.api.types.is_datetime64_dtype(df_clean[col]):
                    column_types[col] = "datetime"
                # Check if column might be convertible to datetime
                elif pd.to_datetime(df_clean[col], errors='coerce').notna().any():
                    column_types[col] = "potential_datetime"
                    # Try to extract a sample date to help with identification
                    sample_dates = pd.to_datetime(df_clean[col], errors='coerce').dropna().head(3)
                    if not sample_dates.empty:
                        column_statistics[col] = {
                            "sample_dates": [d.strftime('%Y-%m-%d') for d in sample_dates]
                        }
                else:
                    column_types[col] = "text"
                    
                # Get a few unique values for each column (useful for identification)
                unique_vals = df_clean[col].dropna().unique()
                if len(unique_vals) > 0:
                    # Limit to 5 values and 100 chars each
                    column_unique_values[col] = [str(val)[:100] for val in unique_vals[:5]]
            except:
                column_types[col] = "unknown"
        
        # Prepare a sample of data - limit to first 5 rows and 200 chars per cell for API limits
        sample_df = df_clean.head(5).copy()
        
        # Convert all data to string with limited length
        for col in sample_df.columns:
            sample_df[col] = sample_df[col].astype(str).apply(lambda x: x[:200] if len(x) > 200 else x)
        
        sample_data = sample_df.to_string()
        
        # Create enhanced context for Gemini with more structured information
        context_info = {
            "column_types": column_types,
            "column_unique_values": column_unique_values,
            "column_statistics": column_statistics
        }
        
        # Create a prompt for Gemini to identify columns with better instructions
        prompt = f"""
        You are a data analysis expert. I have a marketplace sales dataset with the following columns:
        
        Column names and their detected types:
        {json.dumps(column_types, indent=2)}
        
        Sample unique values for columns:
        {json.dumps(column_unique_values, indent=2)}
        
        Statistics for numeric and date columns:
        {json.dumps(column_statistics, indent=2)}
        
        Here's a sample of the data:
        {sample_data}
        
        For a business analytics dashboard, I need to identify which columns contain the following information.
        Analyze both column names and data content to make accurate mappings.
        
        For each category, identify the MOST LIKELY column from my dataset:
        
        1. Sales Amount/Revenue (number representing monetary value of sales)
           - Look for columns with currency values, typically larger numbers
           - May contain terms like: sales, revenue, amount, price, total, value, gmv
           
        2. Order Date/Timestamp (date or time when sale occurred)
           - Look for datetime format columns
           - May contain terms like: date, time, order_date, created_at, timestamp
           
        3. Product Name/ID (identifier for product sold)
           - Usually text columns with product names or IDs
           - May contain terms like: product, item, sku, name, title, description
           
        4. Customer Location/Region (location information for customer)
           - Text columns with location data
           - May contain terms like: location, region, country, state, city, address
           
        5. Sales Channel/Platform (marketplace or platform where sale occurred)
           - Text column with limited unique values representing sales channels
           - May contain terms like: channel, platform, marketplace, store, source, medium
           
        6. Product Category (category or type of product)
           - Text column with category classifications
           - May contain terms like: category, department, type, group, class
           
        7. Order ID (unique identifier for order/transaction)
           - Usually alphanumeric with consistent pattern
           - May contain terms like: order_id, order_number, transaction_id, invoice_id
           
        8. Customer ID (identifier for customer)
           - Usually alphanumeric with consistent pattern
           - May contain terms like: customer_id, buyer_id, user_id, client_id
           
        9. Unit Price (price per unit/item)
           - Numeric column, typically smaller than total sales amount
           - May contain terms like: price, unit_price, rate, item_price
           
        10. Quantity Sold (number of units sold)
            - Typically integer values representing count
            - May contain terms like: quantity, qty, units, count, pieces

        11. Transaction Type/Order Status (indicates transaction status such as returned, cancelled, etc.)
            - Text column with values indicating transaction type or order status
            - May contain terms like: status, order_status, transaction_type, state, return, refund, cancel, replace
            - Look for columns with values like: completed, cancelled, returned, refunded, shipped, delivered, etc.
        
        Please analyze the column names, data types, and sample data carefully.
        Return a JSON object mapping each category to the most likely column name in my dataset. 
        If a category doesn't have a matching column, use null.
        
        Example response format:{
        
            "sales_amount": "Revenue",
            "order_date": "Date",
            "product_name": "Product",
            "customer_location": "Region",
            "sales_channel": "Platform",
            "product_category": "Category",
            "order_id": "OrderID",
            "customer_id": "CustomerID",
            "unit_price": "Price",
            "quantity": "Units",
            "transaction_type": "Order Status"
        }
        
        Include ONLY the JSON object in your response, no additional text.
        """
        
        # Generate response from Gemini
        logger.info("Sending enhanced column identification request to Gemini")
        response = model.generate_content(prompt)
        
        # Extract the JSON from the response
        response_text = response.text
        logger.info(f"Received response from Gemini: {response_text[:200]}...")
        
        # Try to parse the JSON response
        try:
            # Find JSON-like content in the response (it might be surrounded by other text)
            import re
            json_match = re.search(r'({[\s\S]*})', response_text)
            if json_match:
                response_text = json_match.group(1)
                logger.info("Extracted JSON from response")
            
            column_mapping = json.loads(response_text)
            logger.info("Successfully parsed JSON response")
            
            # Validate the mapping - ensure all column names exist in the dataframe
            valid_mapping = {}
            column_confidence = {}  # Add confidence scores
            
            for key, value in column_mapping.items():
                if value is not None:
                    # Check if the exact column name exists
                    if value in df_clean.columns:
                        valid_mapping[key] = value
                        column_confidence[key] = 0.9  # High confidence for exact matches
                        logger.info(f"Mapped {key} to column '{value}'")
                    else:
                        # Try to find a close match (case-insensitive)
                        matches = [col for col in df_clean.columns if str(col).lower() == str(value).lower()]
                        if matches:
                            valid_mapping[key] = matches[0]
                            column_confidence[key] = 0.8  # Good confidence for case-insensitive matches
                            logger.info(f"Mapped {key} to column '{matches[0]}' (case-insensitive match)")
                        else:
                            # Try to find a partial match
                            matches = [col for col in df_clean.columns if str(value).lower() in str(col).lower()]
                            if matches:
                                valid_mapping[key] = matches[0]
                                column_confidence[key] = 0.6  # Lower confidence for partial matches
                                logger.info(f"Mapped {key} to column '{matches[0]}' (partial match)")
                            else:
                                logger.warning(f"Column '{value}' mapped to {key} does not exist in dataframe")
                                valid_mapping[key] = None
                else:
                    valid_mapping[key] = None
            
            # Add confidence scores to the mapping
            valid_mapping['_confidence'] = column_confidence
            
            # Verify data types match expected types for certain fields
            data_type_corrections = []
            
            # Sales amount should be numeric
            if valid_mapping.get('sales_amount') and valid_mapping['sales_amount'] in df_clean.columns:
                col = valid_mapping['sales_amount']
                if not pd.api.types.is_numeric_dtype(df_clean[col]):
                    # Try to convert to numeric to see if it's possible
                    if pd.to_numeric(df_clean[col], errors='coerce').notna().any():
                        logger.info(f"Sales amount column '{col}' can be converted to numeric")
                    else:
                        logger.warning(f"Sales amount column '{col}' is not numeric and cannot be converted")
                        data_type_corrections.append(f"Sales amount column '{col}' may not contain numerical values")
            
            # Order date should be date/time
            if valid_mapping.get('order_date') and valid_mapping['order_date'] in df_clean.columns:
                col = valid_mapping['order_date']
                if not pd.api.types.is_datetime64_dtype(df_clean[col]):
                    # Try to convert to datetime to see if it's possible
                    if pd.to_datetime(df_clean[col], errors='coerce').notna().any():
                        logger.info(f"Order date column '{col}' can be converted to datetime")
                    else:
                        logger.warning(f"Order date column '{col}' is not datetime and cannot be converted")
                        data_type_corrections.append(f"Order date column '{col}' may not contain valid date/time values")
            
            # Add data type warnings to the mapping for user feedback
            if data_type_corrections:
                valid_mapping['_data_type_warnings'] = data_type_corrections
            
            # If we have no successful mappings for critical columns, try the heuristic approach as backup
            if not valid_mapping.get('sales_amount') and not valid_mapping.get('order_date') and not valid_mapping.get('product_name'):
                logger.warning("Gemini failed to identify critical columns, falling back to heuristic approach")
                heuristic_mapping = identify_columns_heuristically(df_clean)
                
                # Merge the mappings, preferring Gemini results when available
                for key in heuristic_mapping:
                    if key not in valid_mapping or valid_mapping[key] is None:
                        valid_mapping[key] = heuristic_mapping[key]
                
                # Add a warning about the fallback
                if '_warnings' not in valid_mapping:
                    valid_mapping['_warnings'] = []
                valid_mapping['_warnings'].append("AI column mapping was supplemented with heuristic detection")
            
            logger.info(f"Final column mapping: {valid_mapping}")
            return valid_mapping
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return identify_columns_heuristically(df_clean)
    
    except Exception as e:
        logger.error(f"Error in Gemini column identification: {e}")
        logger.error(traceback.format_exc())
        return identify_columns_heuristically(df_clean)

def identify_columns_heuristically(df):
    """
    Use heuristics to identify relevant columns when Gemini is not available
    
    Args:
        df: pandas DataFrame containing the sales data
        
    Returns:
        dict: Mapping of analysis categories to column names
    """
    columns = df.columns
    column_mapping = {
        "sales_amount": None,
        "order_date": None,
        "product_name": None,
        "customer_location": None,
        "sales_channel": None,
        "product_category": None,
        "order_id": None,
        "customer_id": None,
        "unit_price": None,
        "quantity": None,
        "transaction_type": None,  # Added transaction_type field
        "_warnings": []
    }
    
    # Check if dataframe is empty or too small
    if df.empty or len(df) < 2 or len(columns) < 2:
        column_mapping["_warnings"].append(f"File contains insufficient data: {len(df)} rows, {len(columns)} columns")
        return column_mapping
    
    # Detect marketplace-specific formats
    marketplace_format = detect_marketplace_format(df)
    if marketplace_format:
        logger.info(f"Detected {marketplace_format} format data")
        
        # Apply marketplace-specific column mappings
        if marketplace_format == "amazon":
            return map_amazon_columns(df, column_mapping)
        elif marketplace_format == "flipkart":
            return map_flipkart_columns(df, column_mapping)
        elif marketplace_format == "meesho":
            return map_meesho_columns(df, column_mapping)
    
    # Check if we're dealing with generic or unnamed columns
    generic_columns = sum(1 for col in columns if 'Unnamed:' in str(col) or 'Column_' in str(col))
    dealing_with_generic_columns = generic_columns > 0 and generic_columns >= len(columns) / 2
    
    if dealing_with_generic_columns:
        logger.info(f"Working with generic columns, using data-based detection: {columns.tolist()}")
        
        # For files with generic column names, we need to analyze the actual data
        # to make educated guesses about the column purposes
        
        # Create a profile of each column to see what it might contain
        column_profiles = {}
        
        for col in columns:
            # Skip completely empty columns
            if df[col].isna().all():
                continue
                
            # Get a sample of non-null values
            sample = df[col].dropna().astype(str).head(30)  # Increased sample size
            if len(sample) == 0:
                continue
            
            # Calculate various statistics for this column
            try:
                # Try to convert to numeric
                numeric_conversion = pd.to_numeric(sample, errors='coerce')
                numeric_success_rate = numeric_conversion.notna().mean()
                
                # Try to convert to datetime
                date_conversion = pd.to_datetime(sample, errors='coerce')
                date_success_rate = date_conversion.notna().mean()
                
                # Check for common patterns
                patterns = {
                    'has_currency': sum(1 for x in sample if any(c in str(x) for c in ['$', '₹', '€', '£', '¥', 'Rs', 'INR'])) / len(sample),
                    'has_product_words': sum(1 for x in sample if any(word in str(x).lower() for word in ['product', 'item', 'sku', 'model', 'brand'])) / len(sample),
                    'has_location_words': sum(1 for x in sample if any(word in str(x).lower() for word in ['city', 'state', 'country', 'pincode', 'zip', 'address'])) / len(sample),
                    'has_date_separators': sum(1 for x in sample if any(sep in str(x) for sep in ['/', '-', '.'])) / len(sample),
                    'word_count': sample.str.split().str.len().mean(),
                    'is_mostly_integers': sum(1 for x in sample if str(x).strip().isdigit()) / len(sample),
                    'avg_length': sample.str.len().mean(),
                    'has_decimal': sum(1 for x in sample if '.' in str(x)) / len(sample),
                    'unique_ratio': min(1.0, len(df[col].dropna().unique()) / len(df[col].dropna())),
                }
                
                # Store the profile
                column_profiles[col] = {
                    'numeric_success': numeric_success_rate,
                    'date_success': date_success_rate,
                    **patterns
                }
                
                # Additional metrics for numeric columns
                if numeric_success_rate > 0.7:  # Mostly numeric
                    numeric_values = numeric_conversion.dropna()
                    if len(numeric_values) > 0:
                        column_profiles[col].update({
                            'mean': numeric_values.mean(),
                            'max': numeric_values.max(),
                            'min': numeric_values.min(),
                            'is_integer': (numeric_values % 1 == 0).all(),
                        })
                
                logger.info(f"Column {col} profile: {column_profiles[col]}")
            except Exception as e:
                logger.error(f"Error profiling column {col}: {e}")
        
        # Now use the profiles to identify columns
        
        # Sales amount - likely numeric with currency symbols or large values
        if not column_mapping["sales_amount"]:
            sales_scores = {}
            for col, profile in column_profiles.items():
                score = 0
                # Currency symbols are strong indicators
                if profile.get('has_currency', 0) > 0:
                    score += 10 * profile['has_currency']
                
                # Indian Rupee symbol is an even stronger indicator
                if profile.get('has_rupee_symbol', 0) > 0:
                    score += 15 * profile['has_rupee_symbol']
                
                # High numeric success rate
                if profile.get('numeric_success', 0) > 0.7:
                    score += 5
                    
                    # Prefer larger values (likely monetary)
                    if profile.get('mean', 0) > 100:
                        score += min(5, profile.get('mean', 0) / 1000)  # Cap the score
                    
                    # Prefer values with decimal points (likely price)
                    if profile.get('has_decimal', 0) > 0.5 and not profile.get('is_integer', True):
                        score += 3
                
                if score > 0:
                    sales_scores[col] = score
            
            if sales_scores:
                best_sales_col = max(sales_scores.items(), key=lambda x: x[1])[0]
                column_mapping["sales_amount"] = best_sales_col
                logger.info(f"Identified sales amount column from generic columns: '{best_sales_col}' with score {sales_scores[best_sales_col]}")
        
        # Order date - likely dates with good conversion rate
        if not column_mapping["order_date"]:
            date_scores = {}
            for col, profile in column_profiles.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                
                score = 0
                # High date conversion success is the strongest indicator
                if profile.get('date_success', 0) > 0.7:
                    score += 10
                
                # Date separators are common in dates
                if profile.get('has_date_separators', 0) > 0.5:
                    score += 3
                
                # Dates tend to have consistent formats/lengths
                if 8 <= profile.get('avg_length', 0) <= 30:  # Common date string lengths
                    score += 2
                
                if score > 0:
                    date_scores[col] = score
            
            if date_scores:
                best_date_col = max(date_scores.items(), key=lambda x: x[1])[0]
                column_mapping["order_date"] = best_date_col
                logger.info(f"Identified order date column from generic columns: '{best_date_col}' with score {date_scores[best_date_col]}")
        
        # Product name - likely text with higher word count and uniqueness
        if not column_mapping["product_name"]:
            product_scores = {}
            for col, profile in column_profiles.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                
                score = 0
                # Product names typically have more words
                if profile.get('word_count', 0) > 2:
                    score += profile.get('word_count', 0)
                
                # Product columns are often unique
                if profile.get('unique_ratio', 0) > 0.5:
                    score += 5 * profile.get('unique_ratio', 0)
                
                # Product-related words are good indicators
                if profile.get('has_product_words', 0) > 0:
                    score += 10 * profile.get('has_product_words', 0)
                
                # Prefer longer text (likely descriptions)
                if profile.get('avg_length', 0) > 15:
                    score += min(5, profile.get('avg_length', 0) / 10)
                
                # Low numeric success rate (likely text)
                if profile.get('numeric_success', 0) < 0.3:
                    score += 2
                
                if score > 0:
                    product_scores[col] = score
            
            if product_scores:
                best_product_col = max(product_scores.items(), key=lambda x: x[1])[0]
                column_mapping["product_name"] = best_product_col
                logger.info(f"Identified product name column from generic columns: '{best_product_col}' with score {product_scores[best_product_col]}")
        
        # Quantity - likely small integers
        if not column_mapping["quantity"]:
            qty_scores = {}
            for col, profile in column_profiles.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                
                score = 0
                # High numeric success and integers are good indicators
                if profile.get('numeric_success', 0) > 0.7 and profile.get('is_integer', False):
                    score += 5
                    
                    # Quantities are typically small numbers
                    if 0 < profile.get('mean', 0) < 100:
                        score += 5
                    
                    # Quantities are typically integers
                    if profile.get('is_mostly_integers', 0) > 0.8:
                        score += 3
                
                if score > 0:
                    qty_scores[col] = score
            
            if qty_scores:
                best_qty_col = max(qty_scores.items(), key=lambda x: x[1])[0]
                column_mapping["quantity"] = best_qty_col
                logger.info(f"Identified quantity column from generic columns: '{best_qty_col}' with score {qty_scores[best_qty_col]}")
        
        # If we've assigned all available columns and still need more, try to guess from data patterns
        if len(columns) <= 5 and all(v is None or v in column_mapping.values() for v in column_mapping.values()):
            # With very few columns, make some educated guesses based on column position
            available_cols = [col for col in columns if col not in column_mapping.values()]
            
            if available_cols and not column_mapping["product_name"]:
                # First available column is often product name
                column_mapping["product_name"] = available_cols[0]
                logger.info(f"Assigned first available column as product name: '{available_cols[0]}'")
                available_cols = available_cols[1:]
            
            if available_cols and not column_mapping["sales_amount"]:
                # Try to find the most numeric column for sales amount
                best_numeric = None
                best_score = 0
                for col in available_cols:
                    if col in column_profiles:
                        score = column_profiles[col].get('numeric_success', 0)
                        if score > best_score:
                            best_score = score
                            best_numeric = col
                
                if best_numeric and best_score > 0.5:
                    column_mapping["sales_amount"] = best_numeric
                    logger.info(f"Assigned most numeric column as sales amount: '{best_numeric}'")
                    available_cols = [c for c in available_cols if c != best_numeric]
    
    # Enhanced patterns for column name matching with more comprehensive keyword lists
    patterns = {
        "sales_amount": [
            "revenue", "sales", "amount", "total", "price*qty", "sale amount", "gmv", "earning", "sales value", 
            "order value", "total price", "gross", "net amount", "total amount", "income", "turnover", "invoice amount",
            "value", "price_total", "grand_total", "final_amount", "item_subtotal", "sale_price", "payment_amount",
            "transaction_amount", "order_amount", "invoice_value", "net_sales", "gross_sales", "total_sales", 
            "amount_payable", "sum", "money", "cash", "paid", "payment", "billing", "bill", "receipt total", 
            "transaction", "cost", "subtotal", "sub-total", "sub_total", "final", "price", "pay", "payment_value"
        ],
        "order_date": [
            "date", "order date", "order time", "timestamp", "time", "ordered", "purchase date", "transaction date",
            "invoice_date", "sales_date", "shipping_date", "date_created", "date_ordered", "payment_date", 
            "order_placed", "purchase_time", "transaction_time", "order_timestamp", "date_time", "creation_date", 
            "booking_date", "created_at", "created", "placed_at", "placed_on", "completed_at", "processed_at",
            "order_at", "checkout_at", "checkout_date", "confirmation_date", "purchased", "sold", "sold_at", 
            "sold_date", "sale_date", "sale_time", "ordered_at", "transaction_at", "invoice_time", "payment_time"
        ],
        "product_name": [
            "product", "item", "name", "title", "sku", "listing", "product name", "item name", "goods", "product_title",
            "item_title", "product_desc", "description", "item_description", "product_details", "product_sku", 
            "product_id", "asin", "item_code", "article", "product_code", "item_id", "model", "variant", "merchandise",
            "good", "stock", "inventory", "catalog", "catalogue", "item_name", "product_name", "goods_name", 
            "product_title", "item_title", "brand", "model_number", "part_number", "isbn", "upc", "ean", "mpn", 
            "commodity", "article_name", "product_description", "item_sku", "product_sku", "merchandise_name"
        ],
        "customer_location": [
            "location", "region", "country", "state", "city", "address", "ship to", "shipping address", "destination",
            "delivery_address", "customer_location", "customer_address", "ship_to_location", "delivery_location",
            "buyer_address", "postal_code", "zip", "zip_code", "pin_code", "pincode", "ship_country", "ship_state", 
            "shipping_region", "geo", "territory", "area", "province", "district", "county", "town", "place", 
            "shipping_city", "shipping_state", "shipping_country", "shipping_zip", "shipping_postal", "billing_city",
            "billing_state", "billing_country", "billing_zip", "billing_postal", "delivery_city", "delivery_region",
            "destination_address", "ship_to_address", "recipient_address", "recipient_location", "customer_region",
            "buyer_location", "buyer_region", "market", "marketplace", "delivery_zone"
        ],
        "sales_channel": [
            "channel", "platform", "marketplace", "store", "source", "medium", "shop", "seller", "venue", "fulfillment",
            "sales_channel", "fulfillment_by", "merchant", "outlet", "marketplace_id", "store_id", "sales_medium",
            "distribution_channel", "business_channel", "retail_channel", "online_store", "pos", "point_of_sale",
            "website", "site", "app", "application", "portal", "shop_name", "shop_id", "vendor", "vendor_id", 
            "supplier", "supplier_id", "reseller", "reseller_name", "partner", "partner_name", "channel_name", 
            "platform_name", "site_name", "marketplace_name", "fulfillment_channel", "selling_channel", "origin",
            "store_name", "store_type", "business_type", "business_model", "seller_type", "sales_type"
        ],
        "product_category": [
            "category", "department", "type", "group", "segment", "class", "division", "product_type", "product_group",
            "product_category", "item_category", "subcategory", "product_class", "product_line", "merchandise_type",
            "item_type", "product_segment", "product_family", "goods_type", "item_classification", "category_name",
            "department_name", "niche", "vertical", "section", "category_id", "category_code", "product_section",
            "product_department", "item_group", "collection", "line", "series", "genre", "style", "classification",
            "taxonomy", "hierarchy", "level", "tier", "subject", "topic", "theme", "kind", "variety", "assortment"
        ],
        "order_id": [
            "order id", "order no", "order number", "transaction id", "txn id", "invoice", "receipt", "reference", 
            "order_id", "transaction_number", "invoice_number", "receipt_number", "order_reference", 
            "order_confirmation", "sales_order", "po_number", "purchase_order", "confirmation_number", 
            "tracking_number", "order_confirmation_id", "ref", "ref_number", "ref_id", "transaction_id", "txn_number",
            "receipt_id", "order_code", "document_number", "document_id", "order_reference", "sales_order_id",
            "so_number", "so_id", "invoice_id", "bill_number", "bill_id", "invoice_ref", "order_key", "billing_id",
            "record_id", "voucher_number", "voucher_id", "receipt_ref", "ticket_number", "ticket_id"
        ],
        "customer_id": [
            "customer", "buyer", "user", "client", "account id", "customer id", "buyer id", "customer_name", 
            "customer_code", "buyer_name", "client_id", "account_number", "customer_reference", "customer_email", 
            "buyer_email", "user_id", "purchaser", "member_id", "buyer_account", "customer_contact", "client_name",
            "client_number", "client_code", "account_id", "account_name", "member_number", "membership_id", 
            "consumer_id", "consumer", "shopper_id", "patron_id", "guest_id", "visitor_id", "buyer_code", 
            "customer_number", "cust_id", "cust_no", "cust_code", "cust_account", "person_id", "contact_id", 
            "individual_id", "household_id", "recipient_id", "end_user", "end_user_id"
        ],
        "unit_price": [
            "price", "unit price", "rate", "item price", "selling price", "cost", "unit cost", "per item", 
            "price_per_unit", "item_price", "unit_rate", "product_price", "base_price", "single_price", "price_each", 
            "sale_rate", "unit_value", "individual_price", "retail_price", "list_price", "mrp", "price_per_item",
            "unit_amount", "per_unit", "each_price", "price_per_piece", "price_per_quantity", "amount_each", 
            "rate_per_unit", "price_per_unit", "per_item_price", "per_item_cost", "item_unit_price", "msrp", 
            "item_rate", "unit_retail", "selling_rate", "unit_selling_price", "per_unit_value", "item_value",
            "price_per_piece", "price_per_item", "value_per_unit"
        ],
        "quantity": [
            "quantity", "qty", "units", "count", "volume", "number of items", "amount", "item_count", "unit_count", 
            "pieces", "order_quantity", "item_quantity", "product_quantity", "number_of_items", "quantity_ordered", 
            "units_sold", "pcs", "quantity_purchased", "order_qty", "number_of_units", "volume_count", "total_quantity",
            "quantity_count", "qty_ordered", "product_count", "item_units", "line_quantity", "item_qty", "num_items", 
            "num_units", "qty_sold", "num_sold", "units_ordered", "pieces_sold", "pieces_ordered", "count_sold", 
            "count_ordered", "item_count", "product_count", "sales_volume", "volume_sold", "nos", "no_of_items", 
            "no_of_units", "number", "num", "amount_ordered", "amount_sold"
        ],
        "transaction_type": [
            "status", "order status", "transaction status", "order_status", "transaction_status", 
            "transaction type", "transaction_type", "order state", "order_state", "state", 
            "return status", "return_status", "fulfillment status", "fulfillment_status",
            "shipment status", "shipment_status", "delivery status", "delivery_status", 
            "order type", "order_type", "payment status", "payment_status", "return", "refund", 
            "cancel", "cancelled", "cancellation", "replace", "replacement","Event Type",
        ],
    }
    
    # If we're not dealing with generic columns, do normal pattern matching
    if not dealing_with_generic_columns:
        # Dataframe analysis statistics for better matching
        column_stats = {}
        
        # Process numeric columns for statistical properties
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            try:
                stats = {
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "is_integer": (df[col] % 1 == 0).mean() > 0.9,  # Check if values are mostly integers
                    "has_negatives": (df[col] < 0).any(),
                    "has_zeros": (df[col] == 0).any(),
                    "unique_ratio": min(1.0, len(df[col].unique()) / len(df[col])),  # Ratio of unique values
                }
                column_stats[col] = stats
            except:
                pass
        
        # Check for datetime convertibility
        for col in df.columns:
            if col not in column_stats:
                try:
                    date_series = pd.to_datetime(df[col], errors='coerce')
                    valid_dates = date_series.notna()
                    if valid_dates.mean() > 0.5:  # If more than 50% convert to dates
                        column_stats[col] = {"is_date": True, "date_ratio": valid_dates.mean()}
                except:
                    pass
        
        # Check string pattern statistics for string columns
        string_columns = df.select_dtypes(include=['object']).columns
        for col in string_columns:
            if col not in column_stats:
                try:
                    sample = df[col].dropna().astype(str).head(100)
                    if len(sample) > 0:
                        # Check if looks like an ID (alphanumeric with consistent length)
                        lengths = sample.str.len()
                        avg_length = lengths.mean()
                        consistent_length = lengths.std() < 2  # Low standard deviation in length
                        
                        # Check for alphanumeric patterns
                        has_letters = sample.str.contains('[a-zA-Z]').mean() > 0.5
                        has_numbers = sample.str.contains('[0-9]').mean() > 0.5
                        
                        column_stats[col] = {
                            "avg_length": avg_length,
                            "consistent_length": consistent_length,
                            "has_letters": has_letters,
                            "has_numbers": has_numbers,
                            "unique_ratio": min(1.0, len(df[col].unique()) / len(df[col])),
                            "avg_word_count": sample.str.split().str.len().mean()
                        }
                except:
                    pass
        
        # First check for exact column matches
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                # Look for exact matches first (case-insensitive)
                exact_matches = [col for i, col in enumerate(columns) if str(col).lower() == pattern]
                if exact_matches:
                    column_mapping[category] = exact_matches[0]
                    logger.info(f"Found exact match for {category}: '{exact_matches[0]}'")
                    break
                
            # If we found a match, continue to next category
            if column_mapping[category]:
                continue
            
            # If no exact match, look for columns containing the pattern
            for pattern in pattern_list:
                partial_matches = [col for col in columns if pattern in str(col).lower()]
                if partial_matches:
                    column_mapping[category] = partial_matches[0]
                    logger.info(f"Found partial match for {category}: '{partial_matches[0]}'")
                    break
    
        # Use statistical features for unmatched columns
        
        # For order_date, use datetime detection
        if not column_mapping["order_date"]:
            date_columns = {col: stats["date_ratio"] for col, stats in column_stats.items() if stats.get("is_date", False)}
            if date_columns:
                best_date_col = max(date_columns.items(), key=lambda x: x[1])[0]
                column_mapping["order_date"] = best_date_col
                logger.info(f"Identified date column based on datetime conversion: '{best_date_col}'")
        
        # For order_id and customer_id, look for high unique ratio columns with consistent length
        id_categories = ["order_id", "customer_id"]
        for category in id_categories:
            if not column_mapping[category]:
                potential_id_cols = {}
                for col, stats in column_stats.items():
                    if col in column_mapping.values():  # Skip already mapped columns
                        continue
                        
                    if not isinstance(stats, dict):
                        continue
                        
                    if stats.get("unique_ratio", 0) > 0.7 and stats.get("consistent_length", False):
                        # Higher score for columns with "id" in the name
                        id_score = stats["unique_ratio"]
                        if "id" in str(col).lower() or "number" in str(col).lower() or "no" in str(col).lower():
                            id_score += 0.2
                        potential_id_cols[col] = id_score
                
                if potential_id_cols:
                    best_id_col = max(potential_id_cols.items(), key=lambda x: x[1])[0]
                    column_mapping[category] = best_id_col
                    logger.info(f"Identified {category} based on unique values and consistent length: '{best_id_col}'")
        
        # For sales_amount, use numeric features
        if not column_mapping["sales_amount"]:
            amount_scores = {}
            for col, stats in column_stats.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                    
                if not isinstance(stats, dict):
                    continue
                    
                if "mean" in stats:  # It's a numeric column
                    # Higher scores for columns with higher values (likely to be monetary)
                    amount_score = 0
                    
                    # Prefer non-integer values (likely monetary with cents)
                    if not stats.get("is_integer", True):
                        amount_score += 2
                    
                    # Prefer positive values
                    if not stats.get("has_negatives", True):
                        amount_score += 1
                    
                    # Prefer values with reasonable magnitude (not too small, not too large)
                    if 0 < stats.get("mean", 0) < 100000:
                        amount_score += 3
                        
                    # Extra weight for larger standard deviation (indicates varying prices)
                    if stats.get("std", 0) > 10:
                        amount_score += 1
                    
                    amount_scores[col] = amount_score
            
            if amount_scores:
                best_amount_col = max(amount_scores.items(), key=lambda x: x[1])[0]
                column_mapping["sales_amount"] = best_amount_col
                logger.info(f"Identified sales amount based on value statistics: '{best_amount_col}'")
        
        # For quantity, look for integer columns with smaller values
        if not column_mapping["quantity"]:
            qty_scores = {}
            for col, stats in column_stats.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                    
                if not isinstance(stats, dict):
                    continue
                    
                if "mean" in stats and stats.get("is_integer", False):  # Integer numeric column
                    qty_score = 0
                    
                    # Prefer smaller values (likely to be quantities)
                    if 0 < stats.get("mean", 0) < 100:
                        qty_score += 4
                    
                    # Prefer positive values only
                    if not stats.get("has_negatives", True):
                        qty_score += 2
                    
                    # Should have some zeros
                    if stats.get("has_zeros", False):
                        qty_score += 1
                    
                    qty_scores[col] = qty_score
            
            if qty_scores:
                best_qty_col = max(qty_scores.items(), key=lambda x: x[1])[0]
                column_mapping["quantity"] = best_qty_col
                logger.info(f"Identified quantity based on integer values: '{best_qty_col}'")
        
        # For product_name, look for text columns with longer values and more words
        if not column_mapping["product_name"]:
            name_scores = {}
            for col, stats in column_stats.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                    
                if not isinstance(stats, dict):
                    continue
                    
                if "avg_length" in stats:  # String column
                    name_score = 0
                    
                    # Prefer longer values
                    if stats.get("avg_length", 0) > 15:
                        name_score += 3
                    
                    # Prefer values with more words
                    if stats.get("avg_word_count", 0) > 2:
                        name_score += 2
                    
                    # Prefer mixed alphanumeric
                    if stats.get("has_letters", False) and stats.get("has_numbers", False):
                        name_score += 1
                    
                    # High unique ratio (almost every product has a unique name)
                    if stats.get("unique_ratio", 0) > 0.5:
                        name_score += 2
                    
                    name_scores[col] = name_score
            
            if name_scores:
                best_name_col = max(name_scores.items(), key=lambda x: x[1])[0]
                column_mapping["product_name"] = best_name_col
                logger.info(f"Identified product name based on text features: '{best_name_col}'")
        
        # For unit_price, look for numeric columns with values less than sales_amount
        if not column_mapping["unit_price"] and column_mapping["sales_amount"] and column_mapping["quantity"]:
            price_scores = {}
            sales_col = column_mapping["sales_amount"]
            qty_col = column_mapping["quantity"]
            
            # If both sales amount and quantity are identified, check for columns that might be unit price
            for col, stats in column_stats.items():
                if col in column_mapping.values():  # Skip already mapped columns
                    continue
                    
                if not isinstance(stats, dict) or "mean" not in stats:
                    continue
                    
                # Check if this column's values multiplied by quantity are close to sales amount
                try:
                    # Calculate average ratio of (price * qty) / total
                    sample_df = df[[col, qty_col, sales_col]].dropna().head(100)
                    if len(sample_df) > 0:
                        sample_df['calculated'] = sample_df[col] * sample_df[qty_col]
                        sample_df['ratio'] = sample_df['calculated'] / sample_df[sales_col]
                        mean_ratio = sample_df['ratio'].mean()
                        
                        # If the average ratio is close to 1, this is likely the unit price
                        if 0.5 < mean_ratio < 1.5:
                            price_scores[col] = 5 - abs(1 - mean_ratio)  # Higher score for closer to 1
                except:
                    continue
            
            if price_scores:
                best_price_col = max(price_scores.items(), key=lambda x: x[1])[0]
                column_mapping["unit_price"] = best_price_col
                logger.info(f"Identified unit price based on price * quantity = total: '{best_price_col}'")
    
    # Provide warnings about missing important columns
    warnings = []
    for key in ["sales_amount", "order_date", "product_name"]:
        if not column_mapping[key]:
            warnings.append(f"Could not identify {key} column")
    
    # Add warnings to the mapping
    if warnings:
        column_mapping["_warnings"] = warnings
        logger.warning(f"Column identification warnings: {warnings}")
    
    return column_mapping

def ensure_json_serializable(data):
    """
    Recursively convert data to ensure it's JSON serializable.
    Handles booleans, numpy values, and other non-serializable types.
    
    Args:
        data: Any data structure to be made JSON serializable
        
    Returns:
        A JSON serializable version of the data
    """
    if isinstance(data, dict):
        return {k: ensure_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ensure_json_serializable(item) for item in data]
    elif isinstance(data, bool):
        # Handle boolean values consistently for JavaScript
        return str(data).lower()
    elif isinstance(data, (int, float, str, type(None))):
        # Handle NaN and infinity values which are not JSON serializable
        if isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
            return None
        return data
    elif "numpy" in str(type(data)):
        # Handle numpy types by converting to Python native types
        try:
            if np.isnan(data) or np.isinf(data):
                return None
            return float(data) if "float" in str(type(data)) else int(data)
        except:
            return str(data)
    elif "datetime" in str(type(data)).lower() or "timestamp" in str(type(data)).lower():
        # Handle datetime objects by converting to ISO format string
        try:
            return data.isoformat()
        except:
            return str(data)
    elif "period" in str(type(data)).lower():
        # Handle pandas Period objects
        try:
            return str(data)
        except:
            return "unknown_period"
    else:
        # Convert any other types to string
        return str(data)

def analyze_sales_data(df, column_mapping, platform_type=None):
    """
    Analyze sales data to extract insights for the dashboard
    
    Args:
        df: pandas DataFrame containing the sales data
        column_mapping: dictionary mapping column types to actual column names
        platform_type: optional platform type for specialized analysis
        
    Returns:
        dict: Dictionary containing analysis results
    """
    # Only normalize column names without modifying the actual data
    df_clean = clean_dataframe(df)
    
    # Print column mapping for debugging
    logger.info(f"Column mapping for analysis: {column_mapping}")
    if platform_type:
        logger.info(f"Analyzing data for platform: {platform_type}")
    
    # Check for data type warnings in column mapping
    if '_data_type_warnings' in column_mapping:
        logger.warning(f"Column data type warnings: {column_mapping['_data_type_warnings']}")
    
    # Check for general warnings in column mapping
    if '_warnings' in column_mapping:
        logger.warning(f"Column mapping warnings: {column_mapping['_warnings']}")
    
    # Initialize analysis structure
    analysis = {
        "summary": {},
        "time_series": {"labels": [], "data": []},
        "top_products": [],
        "top_regions": [],
        "sales_channels": [],
        "order_metrics": {},  # Make sure order_metrics is initialized
        "platform_specific": {}
    }
    
    # Add small dataset warning if needed
    if len(df_clean) < 5:
        analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
            f"Analysis is based on a very small dataset ({len(df_clean)} records). Results may not be statistically significant."
        ]
        logger.warning(f"Analyzing a very small dataset ({len(df_clean)} records)")
    
    try:
        # Generate basic summary stats regardless of column mapping
        analysis["summary"]["row_count"] = len(df_clean)
        analysis["summary"]["column_count"] = len(df_clean.columns)
        
        # For very small datasets, indicate limited reliability
        if len(df_clean) < 5:
            analysis["summary"]["reliability"] = "low"
        elif len(df_clean) < 20:
            analysis["summary"]["reliability"] = "medium"
        else:
            analysis["summary"]["reliability"] = "high"
        
        # Add column mapping to the analysis for reference
        # Filter out meta fields with underscore prefix
        filtered_mapping = {k: v for k, v in column_mapping.items() if not k.startswith('_')}
        analysis["summary"]["column_mapping"] = filtered_mapping
        
        # Print column names and data types for debugging
        logger.info(f"Columns in dataframe: {df_clean.columns.tolist()}")
        logger.info(f"Data types: {df_clean.dtypes.to_dict()}")
        
        # Create a working copy of the dataframe for analysis with potential type conversions
        # This doesn't modify the original data structure, only creates a temporary version for analysis
        df_analysis = df_clean.copy()
        
        # Data type conversions for specific columns (only in the analysis copy)
        # Sales amount to numeric
        sales_col = column_mapping.get('sales_amount')
        if sales_col and sales_col in df_analysis.columns:
            try:
                if not pd.api.types.is_numeric_dtype(df_analysis[sales_col]):
                    logger.info(f"Converting sales column '{sales_col}' to numeric for analysis")
                    # Store original column
                    original_sales = df_analysis[sales_col].copy()
                    # Try to convert, using coerce to handle non-numeric values
                    df_analysis[sales_col] = pd.to_numeric(df_analysis[sales_col], errors='coerce')
                    # Count successful conversions
                    valid_count = df_analysis[sales_col].notna().sum()
                    logger.info(f"Converted {valid_count}/{len(df_analysis)} sales values to numeric")
                    
                    # If too many NaN values after conversion (> 50%), restore original and add warning
                    if valid_count < 0.5 * len(df_analysis):
                        logger.warning(f"Sales column conversion failed for most values, restoring original")
                        df_analysis[sales_col] = original_sales
                        analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                            f"Could not convert sales column '{sales_col}' to numeric"
                        ]
            except Exception as e:
                logger.error(f"Error converting sales column to numeric: {e}")
                analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                    f"Error converting sales column: {str(e)}"
                ]
        
        # Order date to datetime
        date_col = column_mapping.get('order_date')
        if date_col and date_col in df_analysis.columns:
            try:
                if not pd.api.types.is_datetime64_dtype(df_analysis[date_col]):
                    logger.info(f"Converting date column '{date_col}' to datetime for analysis")
                    # Store original column
                    original_dates = df_analysis[date_col].copy()
                    # Try to convert, using coerce to handle non-date values
                    df_analysis[date_col] = pd.to_datetime(df_analysis[date_col], errors='coerce')
                    # Count successful conversions
                    valid_date_count = df_analysis[date_col].notna().sum()
                    logger.info(f"Converted {valid_date_count}/{len(df_analysis)} date values to datetime")
                    
                    # If too many NaN values after conversion (> 50%), restore original and add warning
                    if valid_date_count < 0.5 * len(df_analysis):
                        logger.warning(f"Date column conversion failed for most values, restoring original")
                        df_analysis[date_col] = original_dates
                        analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                            f"Could not convert date column '{date_col}' to datetime"
                        ]
            except Exception as e:
                logger.error(f"Error converting date column to datetime: {e}")
                analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                    f"Error converting date column: {str(e)}"
                ]
        
        # Quantity to numeric
        qty_col = column_mapping.get('quantity')
        if qty_col and qty_col in df_analysis.columns:
            try:
                if not pd.api.types.is_numeric_dtype(df_analysis[qty_col]):
                    logger.info(f"Converting quantity column '{qty_col}' to numeric for analysis")
                    df_analysis[qty_col] = pd.to_numeric(df_analysis[qty_col], errors='coerce')
                    valid_qty_count = df_analysis[qty_col].notna().sum()
                    logger.info(f"Converted {valid_qty_count}/{len(df_analysis)} quantity values to numeric")
            except Exception as e:
                logger.error(f"Error converting quantity column to numeric: {e}")
        
        # Unit price to numeric
        price_col = column_mapping.get('unit_price')
        if price_col and price_col in df_analysis.columns:
            try:
                if not pd.api.types.is_numeric_dtype(df_analysis[price_col]):
                    logger.info(f"Converting unit price column '{price_col}' to numeric for analysis")
                    df_analysis[price_col] = pd.to_numeric(df_analysis[price_col], errors='coerce')
                    valid_price_count = df_analysis[price_col].notna().sum()
                    logger.info(f"Converted {valid_price_count}/{len(df_analysis)} price values to numeric")
            except Exception as e:
                logger.error(f"Error converting unit price column to numeric: {e}")
                
        # Find transaction type column from mapping or through detection
        transaction_type_col = column_mapping.get('transaction_type')
        if not transaction_type_col:
            # Try to find it if not provided in mapping
            for col in df_analysis.columns:
                col_str = str(col).lower()
                if ('status' in col_str or 'state' in col_str or 'type' in col_str) and col_str != 'state' and col_str != 'type':
                    # Check if column contains typical status values
                    unique_vals = df_analysis[col].astype(str).str.lower().unique()
                    status_keywords = ['complete', 'cancel', 'return', 'refund', 'ship', 'deliver', 'process', 'pending']
                    matches = sum(1 for val in unique_vals if any(keyword in val for keyword in status_keywords))
                    
                    # If at least some values match status keywords, use this column
                    if matches > 0:
                        transaction_type_col = col
                        logger.info(f"Auto-detected transaction type column: {col}")
                        break
        
        # Initialize order metrics
        analysis["order_metrics"] = {
            "total_orders": df_analysis.shape[0],
            "regular_orders": df_analysis.shape[0],  # Will be adjusted if we find other order types
            "cancelled_orders": 0,
            "returned_orders": 0,
            "replaced_orders": 0,
            "refunded_orders": 0
        }
        
        # Process transaction types if column is available
        if transaction_type_col and transaction_type_col in df_analysis.columns:
            logger.info(f"Analyzing transaction types from column: {transaction_type_col}")
            
            # Convert to string and lowercase for consistent analysis
            status_values = df_analysis[transaction_type_col].astype(str).str.lower()
            
            # Count various transaction types
            cancelled_mask = status_values.apply(lambda x: 'cancel' in x)
            cancelled_count = cancelled_mask.sum()
            
            replaced_mask = status_values.apply(lambda x: 'replace' in x or 'exchange' in x)
            replaced_count = replaced_mask.sum()
            
            refunded_mask = status_values.apply(lambda x: 'refund' in x or 'money back' in x or 'chargeback' in x)
            refunded_count = refunded_mask.sum()
            
            returned_mask = status_values.apply(lambda x: 'return' in x)
            returned_count = returned_mask.sum()
            
            # Count regular orders (not cancelled, replaced, refunded, or returned)
            problem_orders = cancelled_mask | replaced_mask | refunded_mask | returned_mask
            regular_count = (~problem_orders).sum()
            
            # Calculate total orders
            total_orders = len(status_values)
            
            # Update order metrics
            analysis["order_metrics"]["total_orders"] = int(total_orders)
            analysis["order_metrics"]["regular_orders"] = int(regular_count)
            analysis["order_metrics"]["cancelled_orders"] = int(cancelled_count)
            analysis["order_metrics"]["replaced_orders"] = int(replaced_count)
            analysis["order_metrics"]["refunded_orders"] = int(refunded_count)
            analysis["order_metrics"]["returned_orders"] = int(returned_count)
            
            # Calculate corresponding values if sales column is available
            if sales_col and sales_col in df_analysis.columns:
                try:
                    # Calculate values for different order types
                    if cancelled_count > 0:
                        cancelled_value = float(df_analysis.loc[cancelled_mask, sales_col].sum())
                        analysis["order_metrics"]["cancelled_value"] = cancelled_value
                    
                    if replaced_count > 0:
                        replaced_value = float(df_analysis.loc[replaced_mask, sales_col].sum())
                        analysis["order_metrics"]["replaced_value"] = replaced_value
                    
                    if refunded_count > 0:
                        refunded_value = float(df_analysis.loc[refunded_mask, sales_col].sum())
                        analysis["order_metrics"]["refunded_value"] = refunded_value
                    
                    if returned_count > 0:
                        returned_value = float(df_analysis.loc[returned_mask, sales_col].sum())
                        analysis["order_metrics"]["returned_value"] = returned_value
                    
                    # Calculate rates based on total orders
                    if total_orders > 0:
                        analysis["order_metrics"]["cancellation_rate"] = float(round((cancelled_count / total_orders) * 100, 2))
                        analysis["order_metrics"]["replacement_rate"] = float(round((replaced_count / total_orders) * 100, 2))
                        analysis["order_metrics"]["refund_rate"] = float(round((refunded_count / total_orders) * 100, 2))
                        analysis["order_metrics"]["return_rate"] = float(round((returned_count / total_orders) * 100, 2))
                        
                        # Calculate overall issue rate
                        problem_order_count = cancelled_count + replaced_count + refunded_count + returned_count
                        analysis["order_metrics"]["issue_rate"] = float(round((problem_order_count / total_orders) * 100, 2))
                    
                    logger.info(f"Order metrics - Regular: {regular_count}, Cancelled: {cancelled_count}, " +
                               f"Replaced: {replaced_count}, Refunded: {refunded_count}, Returned: {returned_count}")
                except Exception as e:
                    logger.error(f"Error calculating transaction values: {e}")
            
            # Add transaction type distribution for visualization
            try:
                # Get value counts
                status_counts = status_values.value_counts().reset_index()
                status_counts.columns = ['status', 'count']
                
                # Prepare for visualization (limit to top 5)
                analysis["transaction_types"] = [
                    {
                        "name": str(row['status']),
                        "count": int(row['count']),
                        "percentage": float(round((row['count'] / len(status_values)) * 100, 2))
                    }
                    for _, row in status_counts.head(5).iterrows()
                ]
                
                logger.info(f"Added transaction type distribution with {len(analysis['transaction_types'])} categories")
            except Exception as e:
                logger.error(f"Error creating transaction type distribution: {e}")
        
        # Add return rate and other metrics to the summary for easy access
        if "order_metrics" in analysis and analysis["order_metrics"]:
            if "return_rate" in analysis["order_metrics"]:
                analysis["summary"]["return_rate"] = analysis["order_metrics"]["return_rate"]
            if "cancellation_rate" in analysis["order_metrics"]:
                analysis["summary"]["cancellation_rate"] = analysis["order_metrics"]["cancellation_rate"]
            if "issue_rate" in analysis["order_metrics"]:
                analysis["summary"]["issue_rate"] = analysis["order_metrics"]["issue_rate"]
        
        # Calculate total units if quantity column is available
        if qty_col and qty_col in df_analysis.columns:
            try:
                # Sum total units across all orders
                total_units = df_analysis[qty_col].sum()
                analysis["order_metrics"]["total_units"] = float(total_units)
                logger.info(f"Total units sold: {total_units}")
            except Exception as e:
                logger.error(f"Error calculating total units: {e}")
        
        # Calculate basic summary statistics
        if sales_col and sales_col in df_analysis.columns:
            try:
                # Filter out NaN values in sales column for analysis
                sales_values = df_analysis[sales_col].dropna()
                
                # Count valid sales rows
                valid_sales_rows = len(sales_values)
                logger.info(f"Valid sales values for analysis: {valid_sales_rows} out of {len(df_analysis)}")
                
                if valid_sales_rows > 0:
                    # Calculate basic stats
                    total_sales = sales_values.sum()
                    avg_sale = sales_values.mean()
                    max_sale = sales_values.max()
                    min_sale = sales_values.min()
                    median_sale = sales_values.median()
                    
                    logger.info(f"Sales analysis: Total={total_sales}, Avg={avg_sale}, Max={max_sale}, Min={min_sale}, Median={median_sale}")
                    
                    analysis["summary"]["total_sales"] = float(total_sales)
                    analysis["summary"]["average_sale"] = float(avg_sale)
                    analysis["summary"]["max_sale"] = float(max_sale)
                    analysis["summary"]["min_sale"] = float(min_sale)
                    analysis["summary"]["median_sale"] = float(median_sale)
                    
                    # Number of transactions
                    analysis["summary"]["total_transactions"] = int(valid_sales_rows)
                    
                    # Calculate unit economics if both quantity and sales amount are available
                    qty_col = column_mapping.get('quantity')
                    if qty_col and qty_col in df_analysis.columns:
                        # Create a temporary dataframe with just quantity and sales for analysis
                        temp_df = pd.DataFrame({
                            'quantity': df_analysis[qty_col],
                            'sales': df_analysis[sales_col]
                        }).dropna()
                        
                        if len(temp_df) > 0:
                            total_quantity = temp_df['quantity'].sum()
                            average_order_size = temp_df['quantity'].mean()
                            
                            analysis["summary"]["total_quantity"] = float(total_quantity)
                            analysis["summary"]["average_order_size"] = float(average_order_size)
                            
                            # Calculate average price per unit if sensible
                            if total_quantity > 0:
                                avg_price_per_unit = total_sales / total_quantity
                                analysis["summary"]["average_price_per_unit"] = float(avg_price_per_unit)
                    
                    # Sales by time period (if date column exists)
                    if date_col and date_col in df_analysis.columns:
                        # Create a temporary dataframe with just date and sales for analysis
                        temp_df = pd.DataFrame({
                            'date': df_analysis[date_col],
                            'sales': df_analysis[sales_col]
                        }).dropna()
                        
                        if len(temp_df) > 0:
                            # Get the date range
                            min_date = temp_df['date'].min()
                            max_date = temp_df['date'].max()
                            if pd.notna(min_date) and pd.notna(max_date):
                                try:
                                    analysis["summary"]["date_range"] = {
                                        "start": min_date.strftime('%Y-%m-%d'),
                                        "end": max_date.strftime('%Y-%m-%d')
                                    }
                                    logger.info(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
                                    
                                    # Calculate duration of data in days
                                    duration_days = (max_date - min_date).days
                                    analysis["summary"]["duration_days"] = duration_days
                                    
                                    # Calculate average daily sales
                                    if duration_days > 0:
                                        avg_daily_sales = total_sales / (duration_days + 1)  # +1 to include end date
                                        analysis["summary"]["average_daily_sales"] = float(avg_daily_sales)
                                except Exception as e:
                                    logger.error(f"Error calculating date range: {e}")
                            
                            # Determine appropriate time grouping based on date range
                            if isinstance(min_date, pd.Timestamp) and isinstance(max_date, pd.Timestamp):
                                date_range = (max_date - min_date).days
                                
                                logger.info(f"Date range span: {date_range} days")
                                
                                if date_range > 365*2:  # More than 2 years of data
                                    # Group by quarter
                                    try:
                                        temp_df['period'] = temp_df['date'].dt.to_period('Q').astype(str)
                                        period_format = 'Quarterly'
                                    except:
                                        # Fallback if period conversion fails
                                        temp_df['period'] = temp_df['date'].dt.strftime('%Y-%m')
                                        period_format = 'Monthly'
                                elif date_range > 90:  # More than 3 months of data
                                    # Group by month
                                    temp_df['period'] = temp_df['date'].dt.strftime('%Y-%m')
                                    period_format = 'Monthly'
                                elif date_range > 10:  # More than 10 days of data
                                    # Group by day
                                    temp_df['period'] = temp_df['date'].dt.strftime('%Y-%m-%d')
                                    period_format = 'Daily'
                                else:
                                    # Group by hour for very short time spans
                                    temp_df['period'] = temp_df['date'].dt.strftime('%Y-%m-%d %H:00')
                                    period_format = 'Hourly'
                                
                                # Calculate period sales using pandas groupby
                                period_sales = temp_df.groupby('period')['sales'].sum().reset_index()
                                
                                # Ensure periods are sorted chronologically
                                period_sales = period_sales.sort_values('period')
                                
                                analysis["time_series"]["labels"] = period_sales['period'].tolist()
                                analysis["time_series"]["data"] = [float(x) for x in period_sales['sales'].tolist()]
                                analysis["time_series"]["period_type"] = period_format
                                
                                logger.info(f"Time series analysis: {period_format} periods, {len(period_sales)} data points")
                                
                                # Calculate growth metrics
                                if len(period_sales) > 1:
                                    first_period = period_sales['sales'].iloc[0]
                                    last_period = period_sales['sales'].iloc[-1]
                                    
                                    # Calculate overall growth rate
                                    if first_period > 0:  # Avoid division by zero
                                        growth_rate = ((last_period - first_period) / first_period) * 100
                                        analysis["sales_growth"]["rate"] = float(round(growth_rate, 2))
                                        analysis["sales_growth"]["is_positive"] = "true" if growth_rate > 0 else "false"
                                        logger.info(f"Overall growth rate: {growth_rate:.2f}%")
                                    
                                    # Calculate month-over-month or period-over-period growth
                                    if len(period_sales) >= 3:
                                        # Get the last 3 periods
                                        last_periods = period_sales.tail(3)
                                        current = last_periods['sales'].iloc[2]
                                        previous = last_periods['sales'].iloc[1]
                                        
                                        if previous > 0:
                                            recent_growth = ((current - previous) / previous) * 100
                                            analysis["sales_growth"]["recent_rate"] = float(round(recent_growth, 2))
                                            analysis["sales_growth"]["recent_is_positive"] = "true" if recent_growth > 0 else "false"
                                            logger.info(f"Recent growth rate: {recent_growth:.2f}%")
                                
                                # Add trend analysis (simple linear regression)
                                try:
                                    import numpy as np
                                    from scipy import stats
                                    
                                    # Create X as indexes (0, 1, 2...) and Y as sales values
                                    x = np.arange(len(period_sales))
                                    y = period_sales['sales'].values
                                    
                                    # Perform linear regression
                                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                                    
                                    # Calculate trend metrics
                                    analysis["sales_growth"]["trend"] = {
                                        "slope": float(slope),
                                        "r_squared": float(r_value**2),
                                        "direction": "upward" if slope > 0 else "downward",
                                        "strength": "strong" if abs(r_value) > 0.7 else "moderate" if abs(r_value) > 0.3 else "weak"
                                    }
                                    
                                    # Generate trend line data for visualization
                                    trend_line = [(intercept + slope * i) for i in range(len(period_sales))]
                                    
                                    # Add trend line to time series data
                                    analysis["time_series"]["trend_line"] = [float(round(v, 2)) for v in trend_line]
                                    
                                    # Add moving average for smoothed visualization (if enough data points)
                                    if len(period_sales) >= 5:
                                        window_size = min(3, len(period_sales) // 3)  # Dynamic window size
                                        sales_moving_avg = period_sales['sales'].rolling(window=window_size, center=True).mean()
                                        analysis["time_series"]["moving_average"] = [float(v) if not np.isnan(v) else None for v in sales_moving_avg]
                                    
                                    logger.info(f"Sales trend analysis: direction={analysis['sales_growth']['trend']['direction']}, strength={analysis['sales_growth']['trend']['strength']}")
                                except Exception as e:
                                    logger.error(f"Error in trend analysis: {e}")
                                    logger.error(traceback.format_exc())
                                    
                                # Add period-over-period comparison (if enough data)
                                if len(period_sales) >= 6:
                                    try:
                                        # Calculate period-over-period growth rates
                                        period_sales['previous'] = period_sales['sales'].shift(1)
                                        period_sales['growth_rate'] = ((period_sales['sales'] - period_sales['previous']) / period_sales['previous']) * 100
                                        
                                        # Remove first row with NaN growth rate
                                        growth_rates = period_sales.dropna()
                                        
                                        if len(growth_rates) > 0:
                                            analysis["time_series"]["growth_rates"] = {
                                                "labels": growth_rates['period'].tolist(),
                                                "data": [float(round(x, 2)) for x in growth_rates['growth_rate'].tolist()],
                                                "average": float(round(growth_rates['growth_rate'].mean(), 2))
                                            }
                                    except Exception as e:
                                        logger.error(f"Error in period-over-period analysis: {e}")
                else:
                    logger.warning("No valid sales data found for analysis")
                    analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                        "No valid sales data found for analysis"
                    ]
            except Exception as e:
                logger.error(f"Error analyzing sales data: {e}")
                logger.error(traceback.format_exc())
                analysis["summary"]["error"] = f"Could not analyze sales amount column: {str(e)}"
        else:
            logger.warning(f"Sales column not identified. Available columns: {df_clean.columns.tolist()}")
            analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                "Sales column not identified"
            ]
            
        # Top products analysis using pandas
        product_col = column_mapping.get('product_name')
        if product_col and product_col in df_analysis.columns and sales_col and sales_col in df_analysis.columns:
            try:
                # Create a temporary dataframe for analysis with non-null products and sales
                temp_df = df_analysis[[product_col, sales_col]].dropna()
                
                if len(temp_df) > 0:
                    # Group by product and sum sales using pandas
                    product_sales = temp_df.groupby(product_col)[sales_col].sum().reset_index()
                    
                    # Add count of transactions per product
                    product_count = temp_df.groupby(product_col).size().reset_index(name='transaction_count')
                    product_sales = pd.merge(product_sales, product_count, on=product_col)
                    
                    # Sort by sales amount and take top 10
                    top_products = product_sales.sort_values(by=sales_col, ascending=False).head(10)
                    
                    # Sort by sales amount and take bottom 5
                    bottom_products = product_sales.sort_values(by=sales_col, ascending=True).head(5)
                    
                    logger.info(f"Top products analysis: found {len(top_products)} products")
                    
                    # Format product names to prevent excessively long strings
                    analysis["top_products"] = [
                        {
                            "name": str(row[product_col])[:50] + ('...' if len(str(row[product_col])) > 50 else ''),
                            "value": float(row[sales_col]),
                            "transaction_count": int(row['transaction_count'])
                        }
                        for _, row in top_products.iterrows()
                    ]
                    
                    analysis["bottom_products"] = [
                        {
                            "name": str(row[product_col])[:50] + ('...' if len(str(row[product_col])) > 50 else ''),
                            "value": float(row[sales_col]),
                            "transaction_count": int(row['transaction_count'])
                        }
                        for _, row in bottom_products.iterrows()
                    ]
                    
                    # Calculate product diversity metrics
                    total_products = len(product_sales)
                    analysis["summary"]["total_products"] = total_products
                    
                    # Calculate concentration metrics
                    if total_products > 0:
                        # Top 5 products as percentage of total sales
                        top5_sales = product_sales.nlargest(5, sales_col)[sales_col].sum()
                        top5_pct = (top5_sales / product_sales[sales_col].sum()) * 100
                        analysis["summary"]["top5_products_pct"] = float(round(top5_pct, 2))
                        
                        # Format for visualization - prepare product distribution data
                        all_products_total = product_sales[sales_col].sum()
                        
                        # Get top 5 products for chart
                        top5_products = product_sales.nlargest(5, sales_col)
                        top5_list = [
                            {
                                "name": str(row[product_col])[:30] + ('...' if len(str(row[product_col])) > 30 else ''),
                                "value": float(row[sales_col]),
                                "percentage": float(round((row[sales_col] / all_products_total) * 100, 2))
                            }
                            for _, row in top5_products.iterrows()
                        ]
                        
                        # Add "Others" category for remaining products
                        others_value = all_products_total - top5_sales
                        if others_value > 0:
                            top5_list.append({
                                "name": "Others",
                                "value": float(others_value),
                                "percentage": float(round((others_value / all_products_total) * 100, 2))
                            })
                        
                        # Add pie chart data
                        analysis["product_distribution"] = {
                            "labels": [item["name"] for item in top5_list],
                            "data": [item["value"] for item in top5_list],
                            "percentages": [item["percentage"] for item in top5_list]
                        }
                        
                        logger.info(f"Product concentration: top 5 products = {top5_pct:.2f}% of sales")
            except Exception as e:
                logger.error(f"Error analyzing top products: {e}")
                logger.error(traceback.format_exc())
                analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                    f"Error analyzing products: {str(e)}"
                ]
        
        # Regional analysis using pandas
        region_col = column_mapping.get('customer_location')
        if region_col and region_col in df_analysis.columns and sales_col and sales_col in df_analysis.columns:
            try:
                # Create a temporary dataframe for analysis with non-null regions and sales
                temp_df = df_analysis[[region_col, sales_col]].dropna()
                
                if len(temp_df) > 0:
                    # Group by region and sum sales using pandas
                    region_sales = temp_df.groupby(region_col)[sales_col].sum().reset_index()
                    
                    # Add count of transactions per region
                    region_count = temp_df.groupby(region_col).size().reset_index(name='transaction_count')
                    region_sales = pd.merge(region_sales, region_count, on=region_col)
                    
                    # Sort by sales amount and take top 10
                    top_regions = region_sales.sort_values(by=sales_col, ascending=False).head(10)
                    
                    # Calculate percentage of total sales for each region
                    total_region_sales = region_sales[sales_col].sum()
                    if total_region_sales > 0:
                        top_regions['percentage'] = (top_regions[sales_col] / total_region_sales) * 100
                    
                    logger.info(f"Top regions analysis: found {len(top_regions)} regions")
                    
                    analysis["top_regions"] = [
                        {
                            "name": str(row[region_col])[:50],
                            "value": float(row[sales_col]),
                            "transaction_count": int(row['transaction_count']),
                            "percentage": float(row.get('percentage', 0))
                        }
                        for _, row in top_regions.iterrows()
                    ]
                    
                    # Get the top selling state
                    if len(region_sales) > 0:
                        top_state = region_sales.iloc[0]
                        analysis["order_metrics"]["top_selling_state"] = {
                            "name": str(top_state[region_col])[:50],
                            "value": float(top_state[sales_col]),
                            "transaction_count": int(top_state['transaction_count']),
                            "percentage": float(round((top_state[sales_col] / total_region_sales) * 100, 2)) if total_region_sales > 0 else 0
                        }
                        logger.info(f"Top selling state: {top_state[region_col]} with {top_state[sales_col]} sales")
                    
                    # Get the lowest selling state
                    if len(region_sales) > 1:
                        bottom_state = region_sales.iloc[-1]
                        analysis["order_metrics"]["lowest_selling_state"] = {
                            "name": str(bottom_state[region_col])[:50],
                            "value": float(bottom_state[sales_col]),
                            "transaction_count": int(bottom_state['transaction_count']),
                            "percentage": float(round((bottom_state[sales_col] / total_region_sales) * 100, 2)) if total_region_sales > 0 else 0
                        }
                        logger.info(f"Lowest selling state: {bottom_state[region_col]} with {bottom_state[sales_col]} sales")
                    
                    # Format for visualization - prepare region map data
                    # Create a distribution for the map chart
                    all_regions = region_sales.sort_values(by=sales_col, ascending=False)
                    analysis["region_distribution"] = {
                        "regions": [str(row[region_col]) for _, row in all_regions.iterrows()],
                        "values": [float(row[sales_col]) for _, row in all_regions.iterrows()],
                        "percentages": [float(round((row[sales_col] / total_region_sales) * 100, 2)) for _, row in all_regions.iterrows()]
                    }
                    
                    # For geographic chart visualization - prepare a color-coded dataset
                    if len(all_regions) > 0:
                        # Calculate quartiles for color coding
                        percentiles = [0, 25, 50, 75, 100]
                        # Ensure np is accessible from parent scope
                        import numpy as np
                        thresholds = [np.percentile(all_regions[sales_col], p) for p in percentiles]
                        
                        # Assign color categories based on sales value
                        def get_category(value):
                            for i, threshold in enumerate(thresholds[1:], 1):
                                if value <= threshold:
                                    return i
                            return len(thresholds)
                        
                        all_regions['category'] = all_regions[sales_col].apply(get_category)
                        
                        # Prepare formatted data for map visualization
                        analysis["region_map_data"] = [
                            {
                                "region": str(row[region_col]),
                                "value": float(row[sales_col]),
                                "category": int(row['category']),
                                "percentage": float(round((row[sales_col] / total_region_sales) * 100, 2))
                            }
                            for _, row in all_regions.iterrows()
                        ]
                    
                    # Calculate regional concentration metrics
                    total_regions = len(region_sales)
                    analysis["summary"]["total_regions"] = total_regions
                    
                    # Geographic diversity
                    if total_regions > 0:
                        # Top 3 regions as percentage of total sales
                        top3_region_sales = region_sales.nlargest(3, sales_col)[sales_col].sum()
                        top3_region_pct = (top3_region_sales / total_region_sales) * 100
                        analysis["summary"]["top3_regions_pct"] = float(round(top3_region_pct, 2))
                        
                        logger.info(f"Geographic concentration: top 3 regions = {top3_region_pct:.2f}% of sales")
            except Exception as e:
                logger.error(f"Error analyzing regions: {e}")
                logger.error(traceback.format_exc())
                analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                    f"Error analyzing regions: {str(e)}"
                ]
        
        # Sales channel analysis using pandas
        channel_col = column_mapping.get('sales_channel')
        if channel_col and channel_col in df_analysis.columns and sales_col and sales_col in df_analysis.columns:
            try:
                # Create a temporary dataframe for analysis with non-null channels and sales
                temp_df = df_analysis[[channel_col, sales_col]].dropna()
                
                if len(temp_df) > 0:
                    # Group by channel and sum sales using pandas
                    channel_sales = temp_df.groupby(channel_col)[sales_col].sum().reset_index()
                    
                    # Add count of transactions per channel
                    channel_count = temp_df.groupby(channel_col).size().reset_index(name='transaction_count')
                    channel_sales = pd.merge(channel_sales, channel_count, on=channel_col)
                    
                    # Calculate percentage of total sales for each channel
                    total_channel_sales = channel_sales[sales_col].sum()
                    channel_sales['percentage'] = (channel_sales[sales_col] / total_channel_sales) * 100 if total_channel_sales > 0 else 0
                    
                    # Sort by sales amount in descending order
                    channel_sales = channel_sales.sort_values(by=sales_col, ascending=False)
                    
                    logger.info(f"Sales channel analysis: found {len(channel_sales)} channels")
                    
                    analysis["sales_channels"] = [
                        {
                            "name": str(row[channel_col])[:50],
                            "value": float(row[sales_col]),
                            "transaction_count": int(row['transaction_count']),
                            "percentage": float(row['percentage'])
                        }
                        for _, row in channel_sales.iterrows()
                    ]
                    
                    # Create formatted data for pie/donut chart visualization
                    analysis["channel_distribution"] = {
                        "labels": [str(row[channel_col])[:30] for _, row in channel_sales.iterrows()],
                        "data": [float(row[sales_col]) for _, row in channel_sales.iterrows()],
                        "percentages": [float(round(row['percentage'], 2)) for _, row in channel_sales.iterrows()]
                    }
                    
                    # Calculate channel efficiency (sales per transaction) for bar chart
                    channel_sales['efficiency'] = channel_sales[sales_col] / channel_sales['transaction_count']
                    
                    analysis["channel_efficiency"] = {
                        "labels": [str(row[channel_col])[:30] for _, row in channel_sales.iterrows()],
                        "data": [float(round(row['efficiency'], 2)) for _, row in channel_sales.iterrows()]
                    }
                    
                    # Add channel concentration metrics
                    if len(channel_sales) > 1:
                        # Calculate channel diversity
                        analysis["summary"]["channel_count"] = len(channel_sales)
                        
                        # Percentage of sales from top channel
                        top_channel_pct = float(round(channel_sales.iloc[0]['percentage'], 2))
                        analysis["summary"]["top_channel_pct"] = top_channel_pct
                        
                        logger.info(f"Top sales channel accounts for {top_channel_pct}% of sales")
            except Exception as e:
                logger.error(f"Error analyzing sales channels: {e}")
                logger.error(traceback.format_exc())
                analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                    f"Error analyzing sales channels: {str(e)}"
                ]
        
        # Add platform-specific analysis if platform type is provided
        if platform_type:
            platform_type = platform_type.lower().strip()
            
            if platform_type == 'amazon':
                analysis["platform_specific"] = analyze_amazon_data(df_analysis, column_mapping)
            elif platform_type == 'flipkart':
                analysis["platform_specific"] = analyze_flipkart_data(df_analysis, column_mapping)
            elif platform_type == 'meesho':
                analysis["platform_specific"] = analyze_meesho_data(df_analysis, column_mapping)
            else:
                logger.warning(f"Unknown platform type: {platform_type}")
                analysis["summary"]["warnings"] = analysis["summary"].get("warnings", []) + [
                    f"Unknown platform type: {platform_type}"
                ]
                
        # Create a consolidated key metrics section with all the requested metrics
        key_metrics = {}
        
        # Total orders metrics
        key_metrics["total_orders"] = analysis["order_metrics"].get("total_orders", 0)
        key_metrics["total_units"] = analysis["order_metrics"].get("total_units", analysis["summary"].get("total_quantity", 0))
        
        # Order issue metrics
        key_metrics["total_cancelled_orders"] = analysis["order_metrics"].get("cancelled_orders", 0)
        key_metrics["cancelled_value"] = analysis["order_metrics"].get("cancelled_value", 0)
        key_metrics["total_replacements"] = analysis["order_metrics"].get("replaced_orders", 0)
        key_metrics["replacement_value"] = analysis["order_metrics"].get("replaced_value", 0)
        key_metrics["total_refunded_orders"] = analysis["order_metrics"].get("refunded_orders", 0)
        key_metrics["refunded_value"] = analysis["order_metrics"].get("refunded_value", 0)
        key_metrics["total_returned_orders"] = analysis["order_metrics"].get("returned_orders", 0)
        key_metrics["returned_value"] = analysis["order_metrics"].get("returned_value", 0)
        
        # Sales metrics
        key_metrics["total_sales"] = analysis["summary"].get("total_sales", 0)
        key_metrics["average_sale"] = analysis["summary"].get("average_sale", 0)
        
        # Regional metrics
        if "top_selling_state" in analysis["order_metrics"]:
            key_metrics["top_selling_state"] = analysis["order_metrics"]["top_selling_state"]["name"]
            key_metrics["top_selling_state_value"] = analysis["order_metrics"]["top_selling_state"]["value"]
        
        if "lowest_selling_state" in analysis["order_metrics"]:
            key_metrics["lowest_selling_state"] = analysis["order_metrics"]["lowest_selling_state"]["name"]
            key_metrics["lowest_selling_state_value"] = analysis["order_metrics"]["lowest_selling_state"]["value"]
        
        # Product metrics
        if len(analysis["top_products"]) > 0:
            key_metrics["top_product"] = analysis["top_products"][0]["name"]
            key_metrics["top_product_value"] = analysis["top_products"][0]["value"]
        
        if "bottom_products" in analysis and len(analysis["bottom_products"]) > 0:
            key_metrics["lowest_product"] = analysis["bottom_products"][0]["name"]
            key_metrics["lowest_product_value"] = analysis["bottom_products"][0]["value"]
        
        # Add key metrics to analysis
        analysis["key_metrics"] = key_metrics
        logger.info(f"Generated consolidated key metrics: {key_metrics}")
        
        # Prepare visualization structure for key metrics dashboard display
        analysis["visualization_data"] = {
            "order_metrics": [
                {"label": "Total Orders", "value": key_metrics["total_orders"], "category": "orders"},
                {"label": "Total Units", "value": key_metrics["total_units"], "category": "orders"},
                {"label": "Total Sales", "value": key_metrics["total_sales"], "category": "sales", "format": "currency"},
                {"label": "Average Sale", "value": key_metrics["average_sale"], "category": "sales", "format": "currency"}
            ],
            "issue_metrics": [
                {"label": "Cancelled Orders", "value": key_metrics["total_cancelled_orders"], "category": "issues"},
                {"label": "Cancelled Value", "value": key_metrics["cancelled_value"], "category": "issues", "format": "currency"},
                {"label": "Replacements", "value": key_metrics["total_replacements"], "category": "issues"},
                {"label": "Replacement Value", "value": key_metrics["replacement_value"], "category": "issues", "format": "currency"},
                {"label": "Refunded Orders", "value": key_metrics["total_refunded_orders"], "category": "issues"},
                {"label": "Refunded Value", "value": key_metrics["refunded_value"], "category": "issues", "format": "currency"},
                {"label": "Returned Orders", "value": key_metrics["total_returned_orders"], "category": "issues"},
                {"label": "Returned Value", "value": key_metrics["returned_value"], "category": "issues", "format": "currency"}
            ],
            "region_metrics": [
                {"label": "Top Selling State", "value": key_metrics.get("top_selling_state", "N/A"), "category": "regions"},
                {"label": "Top State Sales", "value": key_metrics.get("top_selling_state_value", 0), "category": "regions", "format": "currency"},
                {"label": "Lowest Selling State", "value": key_metrics.get("lowest_selling_state", "N/A"), "category": "regions"},
                {"label": "Lowest State Sales", "value": key_metrics.get("lowest_selling_state_value", 0), "category": "regions", "format": "currency"}
            ],
            "product_metrics": [
                {"label": "Top Product", "value": key_metrics.get("top_product", "N/A"), "category": "products"},
                {"label": "Top Product Sales", "value": key_metrics.get("top_product_value", 0), "category": "products", "format": "currency"},
                {"label": "Lowest Product", "value": key_metrics.get("lowest_product", "N/A"), "category": "products"},
                {"label": "Lowest Product Sales", "value": key_metrics.get("lowest_product_value", 0), "category": "products", "format": "currency"}
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_sales_data: {e}")
        logger.error(traceback.format_exc())
        
        # Return a basic error analysis
        return {
            "summary": {
                "error": f"Analysis failed: {str(e)}",
                "row_count": len(df) if isinstance(df, pd.DataFrame) else 0,
                "column_count": len(df.columns) if isinstance(df, pd.DataFrame) else 0
            }
        }
    
    # After all analysis is complete, ensure result is JSON serializable before returning
    try:
        # Return the completed analysis after ensuring it's JSON serializable
        return ensure_json_serializable(analysis)
    except Exception as e:
        logger.error(f"Error ensuring JSON serialization in analyze_sales_data: {e}")
        logger.error(traceback.format_exc())
        
        # Return a basic error analysis
        return {
            "summary": {
                "error": f"Analysis failed during JSON serialization: {str(e)}",
                "row_count": len(df) if isinstance(df, pd.DataFrame) else 0,
                "column_count": len(df.columns) if isinstance(df, pd.DataFrame) else 0
            }
        }

def analyze_amazon_data(df, column_mapping):
    """
    Analyze Amazon-specific sales data
    
    Args:
        df: pandas DataFrame containing the Amazon sales data
        column_mapping: dict mapping analysis categories to column names
        
    Returns:
        dict: Amazon-specific analysis results
    """
    logger.info("Running Amazon-specific analysis")
    
    amazon_analysis = {
        "b2b_sales": 0,
        "b2c_sales": 0,
        "cancelled_orders": 0,
        "replacement_orders": 0,
        "refunds": 0,
        "fulfillment_methods": [],
        "order_statuses": [],
        "shipping_categories": []
    }
    
    try:
        # B2B vs B2C sales - look for relevant columns
        sales_col = column_mapping.get('sales_amount')
        if sales_col and sales_col in df.columns:
            # Try to find a B2B identifier column - common patterns in Amazon data
            b2b_col = None
            for col in df.columns:
                col_str = str(col).lower()
                if 'b2b' in col_str or 'business' in col_str or 'fulfilment' in col_str or 'channel' in col_str:
                    b2b_col = col
                    break
            
            if b2b_col:
                logger.info(f"Found potential B2B identifier column: {b2b_col}")
                
                # Create a temporary dataframe for analysis
                temp_df = df[[b2b_col, sales_col]].copy()
                
                # If sales column is not numeric, convert for analysis
                if not pd.api.types.is_numeric_dtype(temp_df[sales_col]):
                    temp_df[sales_col] = pd.to_numeric(temp_df[sales_col], errors='coerce')
                
                # Drop rows with NaN sales
                temp_df = temp_df.dropna(subset=[sales_col])
                
                if len(temp_df) > 0:
                    # Look for B2B identifiers in the column
                    b2b_keywords = ['b2b', 'business', 'amazon business', 'fulfilled by amazon']
                    
                    # Identify B2B sales
                    b2b_mask = temp_df[b2b_col].astype(str).str.lower().apply(
                        lambda x: any(keyword in x for keyword in b2b_keywords)
                    )
                    
                    # Calculate B2B and B2C sales
                    b2b_sales = temp_df.loc[b2b_mask, sales_col].sum()
                    b2c_sales = temp_df.loc[~b2b_mask, sales_col].sum()
                    
                    amazon_analysis["b2b_sales"] = float(b2b_sales)
                    amazon_analysis["b2c_sales"] = float(b2c_sales)
                    amazon_analysis["b2b_percentage"] = float(round(b2b_sales / (b2b_sales + b2c_sales) * 100, 2)) if (b2b_sales + b2c_sales) > 0 else 0
                    
                    # Add B2B vs B2C chart data for visualization
                    amazon_analysis["sales_by_type"] = {
                        "labels": ["B2B", "B2C"],
                        "data": [float(b2b_sales), float(b2c_sales)]
                    }
                    
                    logger.info(f"Amazon B2B sales: {b2b_sales}, B2C sales: {b2c_sales}")
        
        # Fulfillment method analysis
        fulfillment_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'fulfillment' in col_str or 'fulfilled' in col_str or 'ship' in col_str:
                fulfillment_col = col
                break
        
        if fulfillment_col:
            logger.info(f"Found potential fulfillment method column: {fulfillment_col}")
            
            # Get all fulfillment methods
            temp_df = df[fulfillment_col].copy()
            # Group by fulfillment method and count occurrences
            fulfillment_counts = temp_df.astype(str).value_counts().reset_index()
            fulfillment_counts.columns = ['fulfillment_method', 'count']
            
            # Prepare data for visualization
            amazon_analysis["fulfillment_methods"] = [
                {
                    "name": str(row['fulfillment_method']),
                    "count": int(row['count']),
                    "percentage": float(round((row['count'] / len(temp_df)) * 100, 2)) if len(temp_df) > 0 else 0
                }
                for _, row in fulfillment_counts.head(5).iterrows()
            ]
        
        # Cancelled orders
        status_col = None
        # Look for order status column
        for col in df.columns:
            col_str = str(col).lower()
            if 'status' in col_str or 'fulfillment' in col_str or 'state' in col_str or 'order_status' in col_str:
                status_col = col
                break
        
        if status_col:
            logger.info(f"Found potential order status column: {status_col}")
            
            # Count cancelled, replaced, refunded orders
            status_values = df[status_col].astype(str).str.lower()
            
            # Cancelled orders
            cancelled_count = status_values.apply(lambda x: 'cancel' in x).sum()
            amazon_analysis["cancelled_orders"] = int(cancelled_count)
            
            # Replacement orders
            replacement_count = status_values.apply(lambda x: 'replace' in x).sum()
            amazon_analysis["replacement_orders"] = int(replacement_count)
            
            # Refunds
            refund_count = status_values.apply(lambda x: 'refund' in x).sum()
            amazon_analysis["refunds"] = int(refund_count)
            
            # Regular orders (not cancelled, replaced, or refunded)
            regular_count = len(status_values) - cancelled_count - replacement_count - refund_count
            if regular_count < 0:  # Handle overlapping categories
                regular_count = 0
            
            # Add chart data for order statuses
            amazon_analysis["order_statuses"] = [
                {"name": "Regular", "count": int(regular_count)},
                {"name": "Cancelled", "count": int(cancelled_count)},
                {"name": "Replaced", "count": int(replacement_count)},
                {"name": "Refunded", "count": int(refund_count)}
            ]
            
            # Calculate total orders
            total_orders = len(status_values)
            
            # Calculate rates for various order statuses
            if total_orders > 0:
                amazon_analysis["cancellation_rate"] = float(round((cancelled_count / total_orders) * 100, 2))
                amazon_analysis["replacement_rate"] = float(round((replacement_count / total_orders) * 100, 2))
                amazon_analysis["refund_rate"] = float(round((refund_count / total_orders) * 100, 2))
            
            logger.info(f"Amazon order statuses - Cancelled: {cancelled_count}, Replacements: {replacement_count}, Refunds: {refund_count}")
        
        # Shipping category analysis
        shipping_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'ship' in col_str or 'shipping' in col_str or 'delivery' in col_str or 'service' in col_str:
                shipping_col = col
                break
        
        if shipping_col and shipping_col != fulfillment_col:  # Avoid duplicate analysis
            logger.info(f"Found potential shipping category column: {shipping_col}")
            
            # Get shipping categories
            temp_df = df[shipping_col].copy()
            # Group by shipping category and count occurrences
            shipping_counts = temp_df.astype(str).value_counts().reset_index()
            shipping_counts.columns = ['shipping_category', 'count']
            
            # Prepare data for visualization
            amazon_analysis["shipping_categories"] = [
                {
                    "name": str(row['shipping_category']),
                    "count": int(row['count']),
                    "percentage": float(round((row['count'] / len(temp_df)) * 100, 2)) if len(temp_df) > 0 else 0
                }
                for _, row in shipping_counts.head(5).iterrows()
            ]
    
    except Exception as e:
        logger.error(f"Error in Amazon-specific analysis: {e}")
        logger.error(traceback.format_exc())
        amazon_analysis["error"] = str(e)
    
    return amazon_analysis

def analyze_flipkart_data(df, column_mapping):
    """
    Analyze Flipkart-specific sales data
    
    Args:
        df: pandas DataFrame containing the Flipkart sales data
        column_mapping: dict mapping analysis categories to column names
        
    Returns:
        dict: Flipkart-specific analysis results
    """
    logger.info("Running Flipkart-specific analysis")
    
    flipkart_analysis = {
        "shipped_orders": 0,
        "returned_orders": 0,
        "cancelled_orders": 0,
        "return_rate": 0,
        "order_statuses": [],
        "payment_methods": [],
        "delivery_performance": {}
    }
    
    try:
        # Look for order status column
        status_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'status' in col_str or 'state' in col_str or 'order_state' in col_str:
                status_col = col
                break
        
        if status_col:
            logger.info(f"Found potential Flipkart order status column: {status_col}")
            
            # Convert to string and lowercase for consistent analysis
            status_values = df[status_col].astype(str).str.lower()
            
            # Count different order statuses
            shipped_count = status_values.apply(lambda x: 'ship' in x or 'delivered' in x).sum()
            returned_count = status_values.apply(lambda x: 'return' in x).sum()
            cancelled_count = status_values.apply(lambda x: 'cancel' in x).sum()
            
            # Add these to the analysis dictionary
            flipkart_analysis["shipped_orders"] = int(shipped_count)
            flipkart_analysis["returned_orders"] = int(returned_count)
            flipkart_analysis["cancelled_orders"] = int(cancelled_count)
            
            # Calculate return rate
            total_fulfilled = shipped_count + returned_count
            if total_fulfilled > 0:
                flipkart_analysis["return_rate"] = float(round((returned_count / total_fulfilled) * 100, 2))
            
            # Get all unique order statuses for visualization
            status_counts = status_values.value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            
            # Prepare data for chart visualization
            flipkart_analysis["order_statuses"] = [
                {
                    "name": str(row['status']),
                    "count": int(row['count']),
                    "percentage": float(round((row['count'] / len(status_values)) * 100, 2))
                }
                for _, row in status_counts.head(10).iterrows()  # Limit to top 10 statuses
            ]
            
            logger.info(f"Flipkart order counts - Shipped: {shipped_count}, Returned: {returned_count}, Cancelled: {cancelled_count}")
        
        # Payment method analysis
        payment_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'payment' in col_str or 'pay' in col_str or 'mode' in col_str:
                payment_col = col
                break
        
        if payment_col:
            logger.info(f"Found potential payment method column: {payment_col}")
            
            # Get payment method distribution
            payment_values = df[payment_col].astype(str).str.lower()
            payment_counts = payment_values.value_counts().reset_index()
            payment_counts.columns = ['payment_method', 'count']
            
            # Prepare data for visualization
            flipkart_analysis["payment_methods"] = [
                {
                    "name": str(row['payment_method']),
                    "count": int(row['count']),
                    "percentage": float(round((row['count'] / len(payment_values)) * 100, 2))
                }
                for _, row in payment_counts.head(5).iterrows()
            ]
        
        # Look for marketplace fee or commission
        sales_col = column_mapping.get('sales_amount')
        if sales_col and sales_col in df.columns:
            fee_col = None
            for col in df.columns:
                col_str = str(col).lower()
                if 'fee' in col_str or 'commission' in col_str or 'marketplace' in col_str or 'charges' in col_str:
                    fee_col = col
                    break
            
            if fee_col:
                logger.info(f"Found potential Flipkart fee column: {fee_col}")
                
                # Create a temporary dataframe for analysis
                temp_df = df[[fee_col, sales_col]].copy()
                
                # Convert columns to numeric for analysis
                if not pd.api.types.is_numeric_dtype(temp_df[fee_col]):
                    temp_df[fee_col] = pd.to_numeric(temp_df[fee_col], errors='coerce')
                
                if not pd.api.types.is_numeric_dtype(temp_df[sales_col]):
                    temp_df[sales_col] = pd.to_numeric(temp_df[sales_col], errors='coerce')
                
                # Drop rows with NaN values
                temp_df = temp_df.dropna()
                
                if len(temp_df) > 0:
                    # Calculate total fees and fee percentage
                    total_fees = temp_df[fee_col].sum()
                    total_sales = temp_df[sales_col].sum()
                    
                    flipkart_analysis["total_fees"] = float(total_fees)
                    
                    if total_sales > 0:
                        flipkart_analysis["fee_percentage"] = float(round((total_fees / total_sales) * 100, 2))
                        
                        # Add fee vs revenue data for visualization
                        flipkart_analysis["fee_analysis"] = {
                            "labels": ["Revenue", "Marketplace Fees"],
                            "data": [float(total_sales), float(total_fees)]
                        }
                    
                    logger.info(f"Flipkart fees - Total: {total_fees}, Percentage: {flipkart_analysis.get('fee_percentage', 0)}%")
        
        # Delivery performance analysis
        date_col = column_mapping.get('order_date')
        delivery_date_col = None
        
        # Look for delivery date column
        for col in df.columns:
            col_str = str(col).lower()
            if ('delivery' in col_str or 'delivered' in col_str) and 'date' in col_str:
                delivery_date_col = col
                break
        
        if date_col and delivery_date_col and date_col in df.columns and delivery_date_col in df.columns:
            logger.info(f"Analyzing delivery performance with columns: {date_col} and {delivery_date_col}")
            
            # Create temp dataframe with both date columns
            temp_df = df[[date_col, delivery_date_col]].copy()
            
            # Convert to datetime for calculation
            if not pd.api.types.is_datetime64_dtype(temp_df[date_col]):
                temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
            
            if not pd.api.types.is_datetime64_dtype(temp_df[delivery_date_col]):
                temp_df[delivery_date_col] = pd.to_datetime(temp_df[delivery_date_col], errors='coerce')
            
            # Drop rows with NaN values
            temp_df = temp_df.dropna()
            
            if len(temp_df) > 0:
                # Calculate delivery time in days
                temp_df['delivery_days'] = (temp_df[delivery_date_col] - temp_df[date_col]).dt.total_seconds() / (24 * 3600)
                
                # Filter out negative or unreasonable values
                temp_df = temp_df[temp_df['delivery_days'] >= 0]
                temp_df = temp_df[temp_df['delivery_days'] <= 30]  # Assume max 30 days delivery time
                
                if len(temp_df) > 0:
                    # Calculate delivery statistics
                    avg_delivery_time = temp_df['delivery_days'].mean()
                    min_delivery_time = temp_df['delivery_days'].min()
                    max_delivery_time = temp_df['delivery_days'].max()
                    median_delivery_time = temp_df['delivery_days'].median()
                    
                    # Group into delivery time categories
                    delivery_categories = [
                        (0, 2, '0-2 days'),
                        (2, 4, '2-4 days'),
                        (4, 7, '4-7 days'),
                        (7, 14, '7-14 days'),
                        (14, float('inf'), '14+ days')
                    ]
                    
                    category_counts = []
                    for min_days, max_days, label in delivery_categories:
                        count = len(temp_df[(temp_df['delivery_days'] >= min_days) & (temp_df['delivery_days'] < max_days)])
                        category_counts.append({
                            "category": label,
                            "count": int(count),
                            "percentage": float(round((count / len(temp_df)) * 100, 2))
                        })
                    
                    # Add to analysis dictionary
                    flipkart_analysis["delivery_performance"] = {
                        "average_days": float(round(avg_delivery_time, 2)),
                        "median_days": float(round(median_delivery_time, 2)),
                        "min_days": float(round(min_delivery_time, 2)),
                        "max_days": float(round(max_delivery_time, 2)),
                        "distribution": category_counts
                    }
                    
                    logger.info(f"Delivery performance - Avg: {avg_delivery_time:.2f} days, Median: {median_delivery_time:.2f} days")
    
    except Exception as e:
        logger.error(f"Error in Flipkart-specific analysis: {e}")
        logger.error(traceback.format_exc())
        flipkart_analysis["error"] = str(e)
    
    return flipkart_analysis

def analyze_meesho_data(df, column_mapping):
    """
    Analyze Meesho-specific sales data
    
    Args:
        df: pandas DataFrame containing the Meesho sales data
        column_mapping: dict mapping analysis categories to column names
        
    Returns:
        dict: Meesho-specific analysis results
    """
    logger.info("Running Meesho-specific analysis")
    
    meesho_analysis = {
        "cod_orders": 0,
        "prepaid_orders": 0,
        "returned_orders": 0,
        "order_acceptance_rate": 0,
        "payment_methods": [],
        "order_statuses": [],
        "category_performance": [],
        "pricing_tiers": []
    }
    
    try:
        # Look for payment mode column
        payment_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'payment' in col_str or 'mode' in col_str or 'cod' in col_str:
                payment_col = col
                break
        
        if payment_col:
            logger.info(f"Found potential Meesho payment mode column: {payment_col}")
            
            # Convert to string and lowercase for consistent analysis
            payment_values = df[payment_col].astype(str).str.lower()
            
            # Count COD vs prepaid orders
            cod_count = payment_values.apply(lambda x: 'cod' in x or 'cash' in x or 'c.o.d' in x).sum()
            prepaid_count = len(payment_values) - cod_count
            
            meesho_analysis["cod_orders"] = int(cod_count)
            meesho_analysis["prepaid_orders"] = int(prepaid_count)
            meesho_analysis["cod_percentage"] = float(round((cod_count / len(payment_values)) * 100, 2)) if len(payment_values) > 0 else 0
            
            # Add payment method distribution for visualization
            meesho_analysis["payment_methods"] = [
                {"name": "COD", "count": int(cod_count), "percentage": float(round((cod_count / len(payment_values)) * 100, 2)) if len(payment_values) > 0 else 0},
                {"name": "Prepaid", "count": int(prepaid_count), "percentage": float(round((prepaid_count / len(payment_values)) * 100, 2)) if len(payment_values) > 0 else 0}
            ]
            
            logger.info(f"Meesho payment modes - COD: {cod_count}, Prepaid: {prepaid_count}")
        
        # Look for order status column
        status_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'status' in col_str or 'state' in col_str or 'order_state' in col_str:
                status_col = col
                break
        
        if status_col:
            logger.info(f"Found potential Meesho order status column: {status_col}")
            
            # Convert to string and lowercase for consistent analysis
            status_values = df[status_col].astype(str).str.lower()
            
            # Count returned orders
            returned_count = status_values.apply(lambda x: 'return' in x).sum()
            # Count accepted orders
            accepted_count = status_values.apply(lambda x: 'accept' in x or 'ship' in x or 'deliver' in x).sum()
            # Count total orders
            total_orders = len(status_values)
            
            meesho_analysis["returned_orders"] = int(returned_count)
            if total_orders > 0:
                meesho_analysis["order_acceptance_rate"] = float(round((accepted_count / total_orders) * 100, 2))
                meesho_analysis["return_rate"] = float(round((returned_count / total_orders) * 100, 2))
            
            # Get all order statuses for visualization
            status_counts = status_values.value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            
            # Prepare data for visualization
            meesho_analysis["order_statuses"] = [
                {
                    "name": str(row['status']),
                    "count": int(row['count']),
                    "percentage": float(round((row['count'] / len(status_values)) * 100, 2))
                }
                for _, row in status_counts.head(10).iterrows()  # Limit to top 10 statuses
            ]
            
            logger.info(f"Meesho order status - Returned: {returned_count}, Acceptance rate: {meesho_analysis['order_acceptance_rate']}%")
        
        # Category performance analysis
        category_col = column_mapping.get('product_category')
        sales_col = column_mapping.get('sales_amount')
        
        if category_col and sales_col and category_col in df.columns and sales_col in df.columns:
            logger.info(f"Analyzing category performance with columns: {category_col} and {sales_col}")
            
            # Create temp dataframe
            temp_df = df[[category_col, sales_col]].copy()
            
            # Ensure sales column is numeric
            if not pd.api.types.is_numeric_dtype(temp_df[sales_col]):
                temp_df[sales_col] = pd.to_numeric(temp_df[sales_col], errors='coerce')
            
            # Drop NaN values
            temp_df = temp_df.dropna()
            
            if len(temp_df) > 0:
                # Group by category and calculate sales
                category_sales = temp_df.groupby(category_col)[sales_col].agg(['sum', 'count', 'mean']).reset_index()
                category_sales.columns = ['category', 'total_sales', 'order_count', 'avg_order_value']
                
                # Sort by total sales and get top categories
                top_categories = category_sales.sort_values('total_sales', ascending=False).head(10)
                
                # Calculate total sales across all categories
                total_category_sales = category_sales['total_sales'].sum()
                
                # Prepare data for visualization
                meesho_analysis["category_performance"] = [
                    {
                        "name": str(row['category'])[:30],  # Limit length of category name
                        "total_sales": float(row['total_sales']),
                        "order_count": int(row['order_count']),
                        "avg_order_value": float(row['avg_order_value']),
                        "percentage": float(round((row['total_sales'] / total_category_sales) * 100, 2)) if total_category_sales > 0 else 0
                    }
                    for _, row in top_categories.iterrows()
                ]
                
                logger.info(f"Category performance analysis completed for {len(top_categories)} categories")
        
        # Price tier analysis
        price_col = column_mapping.get('unit_price')
        if price_col and price_col in df.columns:
            logger.info(f"Analyzing price tiers with column: {price_col}")
            
            # Create temp dataframe
            temp_df = df[price_col].copy()
            
            # Ensure price column is numeric
            if not pd.api.types.is_numeric_dtype(temp_df):
                temp_df = pd.to_numeric(temp_df, errors='coerce')
            
            # Drop NaN values
            temp_df = temp_df.dropna()
            
            if len(temp_df) > 0:
                # Define price tiers
                price_tiers = [
                    (0, 250, 'Below ₹250'),
                    (250, 500, '₹250 - ₹500'),
                    (500, 1000, '₹500 - ₹1000'),
                    (1000, 2000, '₹1000 - ₹2000'),
                    (2000, float('inf'), 'Above ₹2000')
                ]
                
                # Count products in each tier
                tier_counts = []
                for min_price, max_price, label in price_tiers:
                    count = len(temp_df[(temp_df >= min_price) & (temp_df < max_price)])
                    tier_counts.append({
                        "tier": label,
                        "count": int(count),
                        "percentage": float(round((count / len(temp_df)) * 100, 2))
                    })
                
                # Add to analysis
                meesho_analysis["pricing_tiers"] = tier_counts
                
                logger.info(f"Price tier analysis completed with {len(tier_counts)} tiers")
    
    except Exception as e:
        logger.error(f"Error in Meesho-specific analysis: {e}")
        logger.error(traceback.format_exc())
        meesho_analysis["error"] = str(e)
    
    return meesho_analysis

def detect_marketplace_format(df):
    """
    Detect if the data follows a known marketplace format (Amazon, Flipkart, Meesho)
    
    Args:
        df: pandas DataFrame to analyze
        
    Returns:
        str: Marketplace name if detected, None otherwise
    """
    # Convert column names to lowercase strings for easier pattern matching
    columns_str = ' '.join([str(col).lower() for col in df.columns])
    
    # Check for Amazon-specific columns
    amazon_indicators = ['asin', 'amazon', 'fulfillment', 'seller sku', 'merchant', 'order id', 'marketplace']
    amazon_count = sum(1 for indicator in amazon_indicators if indicator in columns_str)
    
    # Check for Flipkart-specific columns
    flipkart_indicators = ['flipkart', 'fsn', 'order item id', 'invoice amount', 'listing id', 'tcs', 'sku']
    flipkart_count = sum(1 for indicator in flipkart_indicators if indicator in columns_str)
    
    # Check for Meesho-specific columns
    meesho_indicators = ['meesho', 'suborder', 'product price', 'settlement', 'cod', 'customer paid']
    meesho_count = sum(1 for indicator in meesho_indicators if indicator in columns_str)
    
    # Determine the marketplace with the most indicators
    if amazon_count >= 3 and amazon_count > flipkart_count and amazon_count > meesho_count:
        return "amazon"
    elif flipkart_count >= 3 and flipkart_count > amazon_count and flipkart_count > meesho_count:
        return "flipkart"
    elif meesho_count >= 3 and meesho_count > amazon_count and meesho_count > flipkart_count:
        return "meesho"
    
    # Look for marketplace name in data samples if column matching was inconclusive
    try:
        # Check first few rows of string columns
        for col in df.select_dtypes(include=['object']).columns:
            sample = ' '.join(df[col].astype(str).head(5).str.lower().tolist())
            
            if 'amazon' in sample and 'seller central' in sample:
                return "amazon"
            elif 'flipkart' in sample and ('seller hub' in sample or 'seller portal' in sample):
                return "flipkart"
            elif 'meesho' in sample and ('supplier panel' in sample or 'supplier portal' in sample):
                return "meesho"
    except:
        pass
    
    return None

def map_amazon_columns(df, column_mapping):
    """
    Map columns for Amazon format sales data
    
    Args:
        df: pandas DataFrame with Amazon data
        column_mapping: Initial column mapping dict
        
    Returns:
        dict: Updated column mapping
    """
    columns_lower = {str(col).lower(): col for col in df.columns}
    
    # Order date mapping
    date_columns = ['purchase date', 'order date', 'ship date', 'date/time', 'date', 'timestamp']
    for date_col in date_columns:
        if date_col in columns_lower:
            column_mapping['order_date'] = columns_lower[date_col]
            break
    
    # Sales amount mapping
    amount_columns = ['item total', 'total', 'amount', 'price', 'item price', 'item subtotal', 
                     'total amount', 'sale amount', 'product amount', 'item amount']
    for amount_col in amount_columns:
        if amount_col in columns_lower:
            column_mapping['sales_amount'] = columns_lower[amount_col]
            break
    
    # Product mapping
    product_columns = ['product name', 'title', 'item name', 'product title', 'listing', 'asin', 'seller sku']
    for product_col in product_columns:
        if product_col in columns_lower:
            column_mapping['product_name'] = columns_lower[product_col]
            break
    
    # Quantity mapping
    qty_columns = ['quantity', 'qty', 'quantity purchased', 'units', 'qty purchased']
    for qty_col in qty_columns:
        if qty_col in columns_lower:
            column_mapping['quantity'] = columns_lower[qty_col]
            break
    
    # Order ID mapping
    order_columns = ['order id', 'amazon order id', 'order number', 'order-id']
    for order_col in order_columns:
        if order_col in columns_lower:
            column_mapping['order_id'] = columns_lower[order_col]
            break
    
    # Sales channel mapping - usually constant for Amazon but check anyway
    channel_columns = ['fulfillment', 'fulfillment channel', 'ship service level', 'sales channel']
    for channel_col in channel_columns:
        if channel_col in columns_lower:
            column_mapping['sales_channel'] = columns_lower[channel_col]
            break
    
    # Add detection info
    column_mapping['_detected_format'] = 'amazon'
    
    return column_mapping

def map_flipkart_columns(df, column_mapping):
    """
    Map columns for Flipkart format sales data
    
    Args:
        df: pandas DataFrame with Flipkart data
        column_mapping: Initial column mapping dict
        
    Returns:
        dict: Updated column mapping
    """
    columns_lower = {str(col).lower(): col for col in df.columns}
    
    # Order date mapping
    date_columns = ['order date', 'dispatch date', 'shipped date', 'order approve date', 'date']
    for date_col in date_columns:
        if date_col in columns_lower:
            column_mapping['order_date'] = columns_lower[date_col]
            break
    
    # Sales amount mapping - Flipkart has multiple types of amount columns
    amount_columns = ['order item value', 'value', 'invoice amount', 'total amount', 'order amount',
                     'seller invoice amount', 'gross amount', 'sale price', 'product value']
    for amount_col in amount_columns:
        if amount_col in columns_lower:
            column_mapping['sales_amount'] = columns_lower[amount_col]
            break
    
    # Product mapping - Flipkart has FSN and other product identifiers
    product_columns = ['product title', 'product', 'product name', 'title', 'item title', 'display name', 'fsn']
    for product_col in product_columns:
        if product_col in columns_lower:
            column_mapping['product_name'] = columns_lower[product_col]
            break
    
    # Quantity mapping
    qty_columns = ['quantity', 'qty', 'ordered quantity', 'ordered qty', 'units']
    for qty_col in qty_columns:
        if qty_col in columns_lower:
            column_mapping['quantity'] = columns_lower[qty_col]
            break
    
    # Order ID mapping - Flipkart has order ID and order item ID
    order_columns = ['order id', 'order item id', 'flipkart order id', 'order_id']
    for order_col in order_columns:
        if order_col in columns_lower:
            column_mapping['order_id'] = columns_lower[order_col]
            break
    
    # Add detection info
    column_mapping['_detected_format'] = 'flipkart'
    
    return column_mapping

def map_meesho_columns(df, column_mapping):
    """
    Map columns for Meesho format sales data
    
    Args:
        df: pandas DataFrame with Meesho data
        column_mapping: Initial column mapping dict
        
    Returns:
        dict: Updated column mapping
    """
    columns_lower = {str(col).lower(): col for col in df.columns}
    
    # Order date mapping
    date_columns = ['order date', 'shipped date', 'delivery date', 'date of order', 'order timestamp']
    for date_col in date_columns:
        if date_col in columns_lower:
            column_mapping['order_date'] = columns_lower[date_col]
            break
    
    # Sales amount mapping - Meesho has specific amount formats
    amount_columns = ['product price', 'order amount', 'price', 'order value', 'total price', 
                     'customer paid', 'settlement value', 'amount', 'settlement amount']
    for amount_col in amount_columns:
        if amount_col in columns_lower:
            column_mapping['sales_amount'] = columns_lower[amount_col]
            break
    
    # Product mapping
    product_columns = ['product name', 'item name', 'product', 'title', 'description', 'product description']
    for product_col in product_columns:
        if product_col in columns_lower:
            column_mapping['product_name'] = columns_lower[product_col]
            break
    
    # Quantity mapping
    qty_columns = ['quantity', 'qty', 'ordered quantity', 'units', 'product qty']
    for qty_col in qty_columns:
        if qty_col in columns_lower:
            column_mapping['quantity'] = columns_lower[qty_col]
            break
    
    # Order ID mapping - Meesho uses suborder IDs sometimes
    order_columns = ['order id', 'suborder id', 'order_id', 'meesho order id']
    for order_col in order_columns:
        if order_col in columns_lower:
            column_mapping['order_id'] = columns_lower[order_col]
            break
    
    # Customer location is often available in Meesho data
    location_columns = ['state', 'delivery state', 'shipping state', 'customer state', 'shipping address']
    for location_col in location_columns:
        if location_col in columns_lower:
            column_mapping['customer_location'] = columns_lower[location_col]
            break
    
    # Add detection info
    column_mapping['_detected_format'] = 'meesho'
    
    return column_mapping