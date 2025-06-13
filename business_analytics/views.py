from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import pandas as pd
import os
import json
import logging
import traceback
import csv
import tempfile
import io
import sys
from django.conf import settings

from .models import SalesDataFile, SalesAnalysisResult
from .serializers import SalesDataFileSerializer, SalesAnalysisResultSerializer
from .analysis_helper import identify_columns_with_gemini, analyze_sales_data, compute_sales_metrics

# Configure logging
logger = logging.getLogger(__name__)

def debug_print(message):
    """
    Enhanced debug print function that logs messages to the console and collects them for frontend display
    
    This function ensures that debug logs are:
    1. Printed to the terminal for backend monitoring
    2. Collected in a list for potential inclusion in API responses
    3. Properly formatted for readability
    
    Args:
        message: The debug message to log
    """
    # Always print to terminal regardless of DEBUG setting for critical metrics data
    print(f"[ANALYTICS_DEBUG] {message}")
    
    # Log to Django logger
    logger.debug(message)
    
    # In DEBUG mode, also add to a session-based debug log collection
    # (The frontend can retrieve these logs via the debug info in the response)
    if settings.DEBUG:
        if not hasattr(debug_print, 'log_collection'):
            debug_print.log_collection = []
        
        # Add timestamp to log message
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        debug_print.log_collection.append(f"[{timestamp}] {message}")
        
        # Keep only the last 100 messages to avoid memory issues
        if len(debug_print.log_collection) > 100:
            debug_print.log_collection = debug_print.log_collection[-100:]

@method_decorator(csrf_exempt, name='dispatch')
class SalesDataUploadView(APIView):
    """
    API view for handling sales data file uploads and performing analysis
    """
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, format=None):
        """Handle file upload and initiate analysis"""
        try:
            # Check if file was uploaded
            if 'file' not in request.FILES:
                debug_print("No file uploaded in request")
                return Response({"success": False, "error": "No file was uploaded"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the uploaded file
            file_obj = request.FILES['file']
            file_name = file_obj.name
            
            # Get platform type if provided
            platform_type = request.data.get('platform_type', None)
            if platform_type:
                logger.info(f"Platform type specified: {platform_type}")
                debug_print(f"Platform type specified: {platform_type}")
            else:
                logger.info("No platform type specified, using generic analysis")
                debug_print("No platform type specified, using generic analysis")
            
            # Get manual column mapping if provided
            manual_column_mapping = None
            manual_mapping_param = request.data.get('manual_column_mapping', None)
            if manual_mapping_param:
                try:
                    manual_column_mapping = json.loads(manual_mapping_param)
                    logger.info(f"Manual column mapping provided: {manual_column_mapping}")
                    debug_print(f"Manual column mapping provided: {manual_column_mapping}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid manual column mapping format: {manual_mapping_param}")
            
            logger.info(f"Received file upload: {file_name}, size: {file_obj.size} bytes")
            debug_print(f"Processing file upload: {file_name}, size: {file_obj.size} bytes")
            
            # Check file extension
            file_extension = os.path.splitext(file_name)[1].lower()
            if file_extension not in ['.csv', '.xlsx', '.xls']:
                debug_print(f"Unsupported file format: {file_extension}")
                return Response(
                    {"success": False, "error": "Unsupported file format. Please upload CSV or Excel files."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Save the file record
            file_type = file_extension[1:]  # Remove the dot
            sales_file = SalesDataFile.objects.create(
                user=request.user,
                file=file_obj,
                file_name=file_name,
                file_type=file_type
            )
            
            # Create a pending analysis result
            analysis_result = SalesAnalysisResult.objects.create(
                sales_data_file=sales_file,
                status='processing',
                platform_type=platform_type
            )
            
            # Read the file into a pandas DataFrame
            try:
                # Save the file to a temporary location to ensure it can be read multiple times
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    for chunk in file_obj.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                logger.info(f"Saved file temporarily to: {temp_file_path}")
                
                # Now read the file based on its type
                if file_extension == '.csv':
                    # First, try to detect the delimiter
                    with open(temp_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        sample = f.read(4096)
                    
                    sniffer = csv.Sniffer()
                    try:
                        dialect = sniffer.sniff(sample)
                        detected_delimiter = dialect.delimiter
                        logger.info(f"Detected delimiter: '{detected_delimiter}'")
                        debug_print(f"Detected delimiter: '{detected_delimiter}'")
                    except:
                        # Default to comma if detection fails
                        detected_delimiter = ','
                        logger.warning("Failed to detect delimiter, defaulting to comma")
                        debug_print("Failed to detect delimiter, defaulting to comma")
                    
                    # Try to determine if there's a header row
                    try:
                        has_header = sniffer.has_header(sample)
                        logger.info(f"Detected header row: {has_header}")
                    except:
                        has_header = True
                        logger.warning("Failed to detect header, assuming it exists")
                    
                    # Try multiple approaches to read the CSV
                    try:
                        # Try with detected delimiter first
                        logger.info(f"Attempting to read CSV with delimiter: '{detected_delimiter}', header: {0 if has_header else None}")
                        df = pd.read_csv(
                            temp_file_path, 
                            delimiter=detected_delimiter,
                            header=0 if has_header else None,
                            encoding='utf-8',
                            low_memory=False,
                            on_bad_lines='skip'
                        )
                    except Exception as e:
                        logger.error(f"First attempt to read CSV failed: {e}")
                        debug_print(f"First attempt to read CSV failed: {e}")
                        
                        # Try with different encoding
                        logger.info("Attempting to read CSV with latin1 encoding")
                        df = pd.read_csv(
                            temp_file_path,
                            delimiter=detected_delimiter,
                            header=0 if has_header else None,
                            encoding='latin1',
                            low_memory=False,
                            on_bad_lines='skip'
                        )
                    
                    # Check if DataFrame is empty or has no columns
                    if df.empty:
                        logger.error("CSV file resulted in empty DataFrame")
                        debug_print("CSV file resulted in empty DataFrame")
                        raise ValueError("CSV file has no data")
                    
                    if df.shape[1] == 0:
                        logger.error("CSV file resulted in DataFrame with no columns")
                        debug_print("CSV file resulted in DataFrame with no columns")
                        raise ValueError("CSV file has no columns to parse")
                    
                    # If we only have one column, the delimiter might be wrong
                    if df.shape[1] == 1:
                        logger.warning(f"Only one column detected with delimiter '{detected_delimiter}', trying alternatives")
                        debug_print(f"Only one column detected with delimiter '{detected_delimiter}', trying alternatives")
                        # Try some common alternative delimiters
                        for delimiter in [';', '\t', '|']:
                            try:
                                logger.info(f"Trying alternate delimiter: '{delimiter}'")
                                temp_df = pd.read_csv(
                                    temp_file_path,
                                    delimiter=delimiter,
                                    header=0 if has_header else None,
                                    encoding='utf-8',
                                    low_memory=False,
                                    on_bad_lines='skip'
                                )
                                if temp_df.shape[1] > 1:
                                    logger.info(f"Success with delimiter '{delimiter}': {temp_df.shape[1]} columns found")
                                    debug_print(f"Success with delimiter '{delimiter}': {temp_df.shape[1]} columns found")
                                    df = temp_df
                                    break
                            except Exception as e:
                                logger.warning(f"Failed with delimiter '{delimiter}': {e}")
                
                elif file_extension in ['.xlsx', '.xls']:
                    # For Excel files, try with explicit engine and more robust detection
                    logger.info("Reading Excel file with openpyxl engine")
                    
                    # First try to read with default parameters
                    try:
                        df = pd.read_excel(temp_file_path, engine='openpyxl')
                        
                        # Check if we got unnamed columns and few rows, which often indicates
                        # headers or data aren't in the expected location
                        unnamed_cols = sum(1 for col in df.columns if 'Unnamed:' in str(col))
                        
                        # If most columns are unnamed, try reading with different header rows
                        if unnamed_cols > 0 and unnamed_cols >= len(df.columns) / 2:
                            logger.warning(f"Detected {unnamed_cols} unnamed columns, trying alternative header rows")
                            debug_print(f"Detected {unnamed_cols} unnamed columns, trying alternative header rows")
                            
                            # Try with different header row positions
                            for header_row in range(1, 10):  # Try rows 1-9 as header
                                try:
                                    temp_df = pd.read_excel(temp_file_path, engine='openpyxl', header=header_row)
                                    # If we get more named columns, use this dataframe
                                    temp_unnamed = sum(1 for col in temp_df.columns if 'Unnamed:' in str(col))
                                    
                                    if temp_unnamed < unnamed_cols:
                                        logger.info(f"Found better header row at position {header_row}")
                                        debug_print(f"Found better header row at position {header_row}")
                                        df = temp_df
                                        unnamed_cols = temp_unnamed
                                        
                                        # Break if we have no unnamed columns
                                        if unnamed_cols == 0:
                                            break
                                except Exception as e:
                                    logger.warning(f"Error trying header row {header_row}: {e}")
                            
                            # If still mostly unnamed columns, try first row as header and skip rows
                            if unnamed_cols > 0 and unnamed_cols >= len(df.columns) / 2:
                                for skiprows in range(1, 10):
                                    try:
                                        temp_df = pd.read_excel(temp_file_path, engine='openpyxl', header=0, skiprows=skiprows)
                                        temp_unnamed = sum(1 for col in temp_df.columns if 'Unnamed:' in str(col))
                                        
                                        if temp_unnamed < unnamed_cols:
                                            logger.info(f"Found better data skipping {skiprows} rows")
                                            debug_print(f"Found better data skipping {skiprows} rows")
                                            df = temp_df
                                            unnamed_cols = temp_unnamed
                                            
                                            # Break if we have no unnamed columns
                                            if unnamed_cols == 0:
                                                break
                                    except Exception as e:
                                        logger.warning(f"Error trying skiprows {skiprows}: {e}")
                        
                        # Try to detect if the real data is in the second sheet
                        if unnamed_cols > 0 and unnamed_cols >= len(df.columns) / 2:
                            logger.info("Checking if data is in another sheet")
                            debug_print("Checking if data is in another sheet")
                            
                            # Get sheet names
                            import openpyxl
                            workbook = openpyxl.load_workbook(temp_file_path, read_only=True, data_only=True)
                            sheet_names = workbook.sheetnames
                            workbook.close()
                            
                            # If there are multiple sheets, try each one
                            if len(sheet_names) > 1:
                                for sheet_name in sheet_names:
                                    try:
                                        temp_df = pd.read_excel(temp_file_path, engine='openpyxl', sheet_name=sheet_name)
                                        temp_unnamed = sum(1 for col in temp_df.columns if 'Unnamed:' in str(col))
                                        
                                        # If this sheet has more named columns, use it
                                        if temp_unnamed < unnamed_cols and len(temp_df.columns) > 0:
                                            logger.info(f"Found better data in sheet '{sheet_name}'")
                                            debug_print(f"Found better data in sheet '{sheet_name}'")
                                            df = temp_df
                                            unnamed_cols = temp_unnamed
                                            
                                            # Try different header rows on this sheet too
                                            for header_row in range(1, 5):
                                                try:
                                                    sub_temp_df = pd.read_excel(temp_file_path, engine='openpyxl', 
                                                                             sheet_name=sheet_name, header=header_row)
                                                    sub_temp_unnamed = sum(1 for col in sub_temp_df.columns if 'Unnamed:' in str(col))
                                                    
                                                    if sub_temp_unnamed < temp_unnamed:
                                                        logger.info(f"Found better header in sheet '{sheet_name}' at row {header_row}")
                                                        df = sub_temp_df
                                                        break
                                                except Exception as e:
                                                    logger.warning(f"Error trying header row {header_row} in sheet '{sheet_name}': {e}")
                                    except Exception as e:
                                        logger.warning(f"Error reading sheet '{sheet_name}': {e}")
                    
                        # After all attempts, if all columns are still unnamed but we have data,
                        # try to create meaningful column names
                        all_unnamed = all('Unnamed:' in str(col) for col in df.columns)
                        if all_unnamed and len(df) > 0:
                            logger.info("All columns unnamed, creating generic column names")
                            debug_print("All columns unnamed, creating generic column names")
                            
                            # Look at first row to see if it might contain column names
                            if len(df) > 0:
                                first_row = df.iloc[0]
                                if not first_row.isna().all() and isinstance(first_row, pd.Series):
                                    # Use first row as header and skip it
                                    logger.info("Using first data row as header")
                                    debug_print("Using first data row as header")
                                    df.columns = [str(x).strip() if not pd.isna(x) else f"Column_{i}" 
                                               for i, x in enumerate(first_row)]
                                    df = df.iloc[1:].reset_index(drop=True)
                                else:
                                    # Create generic column names based on position
                                    df.columns = [f"Column_{i}" for i in range(len(df.columns))]
                    
                    except Exception as e:
                        logger.error(f"First attempt to read Excel file failed: {e}")
                        debug_print(f"First attempt to read Excel file failed: {e}")
                        
                        # Try with xlrd engine for xls files as fallback
                        if file_extension == '.xls':
                            logger.info("Attempting to read XLS with xlrd engine")
                            try:
                                df = pd.read_excel(temp_file_path, engine='xlrd')
                            except Exception as e2:
                                logger.error(f"Second attempt to read Excel file failed: {e2}")
                                debug_print(f"Second attempt to read Excel file failed: {e2}")
                                raise ValueError(f"Could not read Excel file: {e2}")
                        else:
                            raise ValueError(f"Could not read Excel file: {e}")
                    
                    # Check if DataFrame is empty
                    if df.empty or df.shape[1] == 0:
                        logger.error("Excel file resulted in empty DataFrame or no columns")
                        debug_print("Excel file resulted in empty DataFrame or no columns")
                        raise ValueError("Excel file has no data or no columns could be parsed")
                        
                    # Debug: print the detected column names
                    debug_print(f"Final detected columns: {df.columns.tolist()}")
                    debug_print(f"Data types: {df.dtypes.to_dict()}")
                else:
                    raise ValueError(f"Unsupported file extension: {file_extension}")
                
                # Remove the temporary file
                try:
                    os.unlink(temp_file_path)
                    logger.info("Temporary file removed")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {e}")
                
                # Log DataFrame info for debugging
                logger.info(f"Successfully read file with shape: {df.shape}")
                debug_print(f"Successfully read file with shape: {df.shape}")
                debug_print(f"Columns: {df.columns.tolist()}")
                
                # Print sample data for debugging
                sample_data = df.head(5).to_string()
                debug_print(f"Sample data:\n{sample_data}")
                
                # Initialize column_mapping early to avoid "referenced before assignment" error
                column_mapping = {}
                column_mapping_issues = []
                
                # Check if we have enough data to analyze
                if df.shape[0] < 5:
                    logger.warning(f"File contains very few records: {df.shape[0]} (minimum 5 recommended)")
                    debug_print(f"File contains very few records: {df.shape[0]} (minimum 5 recommended)")
                    
                    # Add a warning instead of throwing an error
                    if '_warnings' not in column_mapping:
                        column_mapping['_warnings'] = []
                    column_mapping['_warnings'].append(f"File contains only {df.shape[0]} records. Analysis may be limited.")
                    
                    # Add to the issues list for UI display
                    column_mapping_issues.append(f"File contains only {df.shape[0]} records. Analysis results may be limited.")
                    
                    # Continue processing - no need to raise an exception
                
                # Preprocess the dataframe - clean column names for consistency
                # This won't change the actual data, just normalizes column names
                clean_df = df.copy()
                clean_df.columns = [str(col).strip().replace('\n', ' ') for col in clean_df.columns]
                
                # Identify columns using Gemini AI - only for column identification
                logger.info("Starting column identification with Gemini")
                column_mapping = identify_columns_with_gemini(clean_df, platform_type=platform_type)
                logger.info(f"Column mapping result: {column_mapping}")
                debug_print(f"Column mapping result: {json.dumps(column_mapping, indent=2)}")
                
                # Apply manual column mapping if provided
                if manual_column_mapping:
                    # Override automatic mapping with manual mapping
                    for key, value in manual_column_mapping.items():
                        if value:  # Only override if a value was actually provided
                            column_mapping[key] = value
                            logger.info(f"Manual override for {key}: {value}")
                    
                    debug_print(f"Column mapping after manual overrides: {json.dumps(column_mapping, indent=2)}")
                
                # Check for warnings or data type issues in column mapping
                column_mapping_issues = []
                
                # Extract warnings from the column mapping
                if '_warnings' in column_mapping:
                    column_mapping_issues.extend(column_mapping['_warnings'])
                
                # Extract data type warnings from the column mapping
                if '_data_type_warnings' in column_mapping:
                    column_mapping_issues.extend(column_mapping['_data_type_warnings'])
                
                # Validate critical columns are present
                if not column_mapping.get('sales_amount'):
                    column_mapping_issues.append("Sales amount column could not be identified. Analysis may be limited.")
                
                if not column_mapping.get('order_date'):
                    column_mapping_issues.append("Order date column could not be identified. Time-based analysis will be unavailable.")
                
                if not column_mapping.get('product_name'):
                    column_mapping_issues.append("Product name/ID column could not be identified. Product-based analysis will be unavailable.")
                
                # For Excel files with few columns or mostly unnamed columns, add a specific message
                unnamed_cols = sum(1 for col in clean_df.columns if 'Unnamed:' in str(col) or 'Column_' in str(col))
                if unnamed_cols > 0 and unnamed_cols >= len(clean_df.columns) / 2:
                    column_mapping_issues.append("Your Excel file contains unnamed columns. Consider adding header row with descriptive column names.")
                    logger.warning("Excel file contains mostly unnamed columns")
                    debug_print("Excel file contains mostly unnamed columns")
                    
                    # Add some more specific suggestions
                    if file_extension in ['.xlsx', '.xls']:
                        # Provide guidance on typical Excel file issues
                        column_mapping_issues.append("Try ensuring the first row contains headers and there are no merged cells or blank rows at the top.")
                        
                        # Show the available columns to help with debugging
                        available_cols_str = ", ".join([str(col) for col in clean_df.columns])
                        debug_print(f"Available columns in Excel file: {available_cols_str}")
                
                # Log issues found during column mapping
                if column_mapping_issues:
                    logger.warning(f"Column mapping issues: {column_mapping_issues}")
                    debug_print(f"Column mapping issues: {column_mapping_issues}")
                    
                    # For files with few columns, give more specific mapping instructions
                    if len(clean_df.columns) <= 5:
                        debug_print(f"Excel file contains only {len(clean_df.columns)} columns. Consider using manual column mapping.")
                        column_mapping_issues.append(f"Your file contains only {len(clean_df.columns)} columns. Please use the Advanced Options to manually map columns.")
                
                # Analyze the data using pandas
                logger.info("Starting data analysis with pandas")
                try:
                    analysis_data = analyze_sales_data(clean_df, column_mapping, platform_type)
                    logger.info("Data analysis completed")
                    
                    # Add column mapping issues to the analysis summary
                    if column_mapping_issues:
                        if 'summary' not in analysis_data:
                            analysis_data['summary'] = {}
                        analysis_data['summary']['column_mapping_issues'] = column_mapping_issues
                    
                    # Debug print the analysis data
                    try:
                        debug_print(f"Analysis data (summary):\n{json.dumps(analysis_data.get('summary', {}), indent=2)}")
                        if 'time_series' in analysis_data and 'labels' in analysis_data['time_series']:
                            debug_print(f"Time series data: {len(analysis_data['time_series']['labels'])} periods")
                        debug_print(f"Top products: {len(analysis_data.get('top_products', []))} items")
                        debug_print(f"Top regions: {len(analysis_data.get('top_regions', []))} items")
                        debug_print(f"Sales channels: {len(analysis_data.get('sales_channels', []))} items")
                        if platform_type:
                            debug_print(f"Platform-specific data: {json.dumps(analysis_data.get('platform_specific', {}), indent=2)}")
                    except TypeError as e:
                        logger.error(f"Error printing analysis data: {e}")
                        debug_print(f"Error printing analysis data: {e}")
                except Exception as analysis_error:
                    logger.error(f"Error in data analysis: {analysis_error}")
                    debug_print(f"Error in data analysis: {analysis_error}")
                    debug_print(traceback.format_exc())
                    
                    # Provide a basic analysis structure if analysis fails
                    analysis_data = {
                        "summary": {
                            "error": f"Analysis error: {str(analysis_error)}",
                            "row_count": len(clean_df),
                            "column_count": len(clean_df.columns),
                            "column_mapping_issues": column_mapping_issues
                        }
                    }
                
                # Update the analysis result
                analysis_result.column_mappings = column_mapping
                analysis_result.analysis_data = analysis_data
                analysis_result.status = 'completed'
                analysis_result.save()
                
                logger.info("Analysis completed and saved to database")
                
                # Prepare response
                response_data = {
                    "success": True,
                    "message": "File uploaded and analyzed successfully",
                    "file_id": str(sales_file.id),
                    "analysis_id": str(analysis_result.id),
                    "column_mapping": {k: v for k, v in column_mapping.items() if not k.startswith('_')},  # Filter out metadata fields
                    "column_mapping_issues": column_mapping_issues if column_mapping_issues else None,
                    "analysis": analysis_data,
                    "platform_type": platform_type,
                    "available_columns": clean_df.columns.tolist()  # Include all available columns in response
                }
                
                # Debug print the response status
                debug_print("Sending successful response with analysis data")
                
                # Ensure we can serialize the data properly
                try:
                    # Test JSON serialization to catch any issues
                    json_string = json.dumps(response_data)
                    debug_print(f"Successfully serialized response data ({len(json_string)} bytes)")
                except Exception as json_error:
                    logger.error(f"JSON serialization error: {json_error}")
                    debug_print(f"JSON serialization error: {json_error}")
                    
                    # Try to identify which key is causing the serialization error
                    problematic_keys = []
                    for key in response_data:
                        try:
                            json.dumps(response_data[key])
                        except Exception as key_error:
                            problematic_keys.append(key)
                            logger.error(f"Serialization error in key '{key}': {key_error}")
                            debug_print(f"Serialization error in key '{key}': {key_error}")
                            
                            # If it's the analysis, try to identify which subkey is problematic
                            if key == 'analysis' and isinstance(response_data[key], dict):
                                for subkey in response_data[key]:
                                    try:
                                        json.dumps(response_data[key][subkey])
                                    except Exception as subkey_error:
                                        logger.error(f"Serialization error in analysis.{subkey}: {subkey_error}")
                                        debug_print(f"Serialization error in analysis.{subkey}: {subkey_error}")
                    
                    debug_print(f"Problematic keys identified: {problematic_keys}")
                    
                    # Find the problematic field and sanitize it
                    sanitized_data = self.sanitize_data_for_json(response_data)
                    
                    # Try again with sanitized data
                    try:
                        json_string = json.dumps(sanitized_data)
                        debug_print(f"Successfully serialized sanitized data ({len(json_string)} bytes)")
                        return Response(sanitized_data, status=status.HTTP_200_OK)
                    except Exception as second_error:
                        logger.error(f"Second JSON serialization error: {second_error}")
                        debug_print(f"Second JSON serialization error: {second_error}")
                        
                        # Provide a simplified response if serialization failed
                        return Response({
                            "success": True,
                            "message": "Analysis completed but results couldn't be fully serialized",
                            "file_id": str(sales_file.id),
                            "analysis_id": str(analysis_result.id),
                            "column_mapping_issues": column_mapping_issues if column_mapping_issues else None,
                            "platform_type": platform_type,
                            "available_columns": clean_df.columns.tolist()
                        }, status=status.HTTP_200_OK)
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Exception as e:
                # Log the error
                logger.error(f"Error analyzing file {file_name}: {e}")
                logger.error(traceback.format_exc())
                debug_print(f"Error analyzing file {file_name}: {e}")
                debug_print(traceback.format_exc())
                
                # Update the analysis result with error
                analysis_result.status = 'failed'
                analysis_result.error_message = str(e)
                analysis_result.save()
                
                return Response(
                    {"success": False, "error": f"Error analyzing file: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            # Log the error
            logger.error(f"Error in file upload: {e}")
            logger.error(traceback.format_exc())
            debug_print(f"Error in file upload: {e}")
            debug_print(traceback.format_exc())
            
            return Response(
                {"success": False, "error": f"Error processing upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def sanitize_data_for_json(self, data):
        """
        Recursively sanitize data to ensure it can be JSON serialized
        """
        if isinstance(data, dict):
            return {k: self.sanitize_data_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_data_for_json(item) for item in data]
        elif isinstance(data, bool):
            # Explicitly convert boolean values to strings to avoid serialization issues
            return str(data).lower()  # Returns "true" or "false"
        elif isinstance(data, (int, float, str, type(None))):
            return data
        else:
            # Convert non-serializable types to strings
            try:
                return str(data)
            except:
                return "Non-serializable data"

@method_decorator(login_required, name='dispatch')
class BusinessAnalyticsView(APIView):
    """
    View for rendering the business analytics dashboard
    """
    def get(self, request, format=None):
        # Get the user's most recent analysis result
        recent_analysis = SalesAnalysisResult.objects.filter(
            sales_data_file__user=request.user,
            status='completed'
        ).order_by('-created_at').first()
        
        if recent_analysis:
            logger.info(f"Found recent analysis for user {request.user.username}: {recent_analysis.id}")
            debug_print(f"Found recent analysis for user {request.user.username}: {recent_analysis.id}")
            
            # Check if analysis_data is valid
            analysis_data = recent_analysis.analysis_data
            if analysis_data:
                debug_print(f"Analysis data available: {json.dumps(analysis_data.get('summary', {}), indent=2)}")
                if 'time_series' in analysis_data:
                    ts_data = analysis_data['time_series']
                    if 'labels' in ts_data and 'data' in ts_data:
                        debug_print(f"Time series data available: {len(ts_data['labels'])} periods with {len(ts_data['data'])} data points")
                    else:
                        debug_print("Time series data structure is incomplete")
                else:
                    debug_print("No time series data available in analysis")
            else:
                debug_print("Analysis data is empty or None")
        else:
            logger.info(f"No completed analysis found for user {request.user.username}")
            debug_print(f"No completed analysis found for user {request.user.username}")
        
        context = {
            'recent_analysis': recent_analysis
        }
        
        # Debug print the context data sent to the template
        if recent_analysis and recent_analysis.analysis_data:
            debug_print("Context includes analysis data that will be available in the template")
        
        return render(request, 'business_analytics/dashboard.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class AnalysisResultView(APIView):
    """
    API view for retrieving analysis results
    """
    def get(self, request, analysis_id=None, format=None):
        try:
            if analysis_id:
                # Get the specified analysis result
                analysis = SalesAnalysisResult.objects.filter(
                    id=analysis_id,
                    sales_data_file__user=request.user
                ).first()
                
                if not analysis:
                    logger.warning(f"Analysis not found: {analysis_id} for user {request.user.username}")
                    debug_print(f"Analysis not found: {analysis_id} for user {request.user.username}")
                    return Response({"error": "Analysis not found"}, status=status.HTTP_404_NOT_FOUND)
                
                logger.info(f"Returning analysis {analysis_id} for user {request.user.username}")
                debug_print(f"Returning analysis {analysis_id} for user {request.user.username}")
                serializer = SalesAnalysisResultSerializer(analysis)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # Get all analysis results for the user
                analyses = SalesAnalysisResult.objects.filter(
                    sales_data_file__user=request.user
                ).order_by('-created_at')
                
                logger.info(f"Returning {analyses.count()} analyses for user {request.user.username}")
                debug_print(f"Returning {analyses.count()} analyses for user {request.user.username}")
                serializer = SalesAnalysisResultSerializer(analyses, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
                
        except Exception as e:
            # Log the error
            logger.error(f"Error retrieving analysis: {e}")
            logger.error(traceback.format_exc())
            debug_print(f"Error retrieving analysis: {e}")
            debug_print(traceback.format_exc())
            
            return Response(
                {"error": f"Error retrieving analysis: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class SalesMetricsView(APIView):
    """
    API view for computing specific sales metrics from an uploaded file
    """
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, format=None):
        """Handle file upload and compute metrics"""
        try:
            # Check platform type for special handling
            platform_type = request.data.get('platform_type', '').lower()
            
            # Special handling for Meesho platform (dual file upload)
            if platform_type == 'meesho':
                return self.handle_meesho_files(request)
            
            # Standard handling for other platforms (single file)
            # Check if file was uploaded
            if 'file' not in request.FILES:
                debug_print("No file uploaded in request")
                return Response({"error": "No file was uploaded"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the uploaded file
            file_obj = request.FILES['file']
            file_name = file_obj.name
            
            # Get manual column mapping if provided
            manual_column_mapping = None
            manual_mapping_param = request.data.get('manual_column_mapping', None)
            if manual_mapping_param:
                try:
                    manual_column_mapping = json.loads(manual_mapping_param)
                    logger.info(f"Manual column mapping provided: {manual_column_mapping}")
                    debug_print(f"Manual column mapping provided: {manual_column_mapping}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid manual column mapping format: {manual_mapping_param}")
            
            logger.info(f"Computing sales metrics for file: {file_name}, size: {file_obj.size} bytes")
            debug_print(f"Computing sales metrics for file: {file_name}, size: {file_obj.size} bytes")
            
            # Check file extension
            file_extension = os.path.splitext(file_name)[1].lower()
            if file_extension not in ['.csv', '.xlsx', '.xls']:
                debug_print(f"Unsupported file format: {file_extension}")
                return Response({"error": "Unsupported file format. Please upload CSV or Excel files."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Process the file and read it into a pandas DataFrame
            try:
                # Save the file to a temporary location
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    for chunk in file_obj.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                logger.info(f"Saved file temporarily to: {temp_file_path}")
                
                # Determine the file type and read accordingly
                df = None
                if file_extension == '.csv':
                    # Use the same CSV reading logic from the upload view
                    with open(temp_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        sample = f.read(4096)
                    
                    sniffer = csv.Sniffer()
                    try:
                        dialect = sniffer.sniff(sample)
                        detected_delimiter = dialect.delimiter
                        logger.info(f"Detected delimiter: '{detected_delimiter}'")
                    except:
                        detected_delimiter = ','
                        logger.warning("Failed to detect delimiter, defaulting to comma")
                    
                    try:
                        has_header = sniffer.has_header(sample)
                    except:
                        has_header = True
                    
                    # Try with detected settings
                    try:
                        df = pd.read_csv(
                            temp_file_path, 
                            delimiter=detected_delimiter,
                            header=0 if has_header else None,
                            encoding='utf-8',
                            low_memory=False,
                            on_bad_lines='skip'
                        )
                    except Exception as e:
                        logger.error(f"First attempt to read CSV failed: {e}")
                        
                        # Try with different encoding
                        df = pd.read_csv(
                            temp_file_path,
                            delimiter=detected_delimiter,
                            header=0 if has_header else None,
                            encoding='latin1',
                            low_memory=False,
                            on_bad_lines='skip'
                        )
                    
                    # Try alternative delimiters if needed
                    if df.shape[1] == 1:
                        for delimiter in [';', '\t', '|']:
                            try:
                                temp_df = pd.read_csv(
                                    temp_file_path,
                                    delimiter=delimiter,
                                    header=0 if has_header else None,
                                    encoding='utf-8',
                                    low_memory=False,
                                    on_bad_lines='skip'
                                )
                                if temp_df.shape[1] > 1:
                                    df = temp_df
                                    break
                            except:
                                pass
                
                elif file_extension in ['.xlsx', '.xls']:
                    # Read Excel file
                    try:
                        df = pd.read_excel(temp_file_path, engine='openpyxl')
                    except:
                        # Fallback to xlrd for older Excel files
                        df = pd.read_excel(temp_file_path, engine='xlrd')
                
                # Clean up the temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    logger.warning(f"Failed to delete temporary file: {temp_file_path}")
                
                # Validate the DataFrame
                if df is None or df.empty:
                    logger.error("File resulted in empty DataFrame")
                    return Response({"error": "File contains no data or is in an unsupported format."}, status=status.HTTP_400_BAD_REQUEST)
                
                # Identify columns
                if manual_column_mapping:
                    column_mapping = manual_column_mapping
                else:
                    # Use AI or heuristic column identification with platform type
                    column_mapping = identify_columns_with_gemini(df, platform_type=platform_type)
                
                # Compute the sales metrics
                metrics = compute_sales_metrics(df, column_mapping)
                
                # Return ONLY the metrics object as requested, with no additional fields
                return Response(metrics, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}")
                logger.error(traceback.format_exc())
                return Response({"error": f"Error processing file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def handle_meesho_files(self, request):
        """
        Special handler for Meesho platform that requires two files:
        1. Sales data file
        2. Returns/cancellations data file
        
        This method processes both files, merges them, and then performs the analysis.
        The returns file should have the same columns as the sales file, plus an additional
        'cancel_return_date' column.
        """
        try:
            debug_print("🟢 Meesho platform selected")
            
            # Validate that both files are present
            if 'sales_file' not in request.FILES or 'returns_file' not in request.FILES:
                debug_print("❌ Missing required files for Meesho analysis")
                return Response({
                    "error": "Please upload two files – (1) Sales Data, and (2) Sales Return/Cancellation Data."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get both uploaded files
            sales_file = request.FILES['sales_file']
            returns_file = request.FILES['returns_file']
            
            # Log file information
            debug_print(f"Uploaded Meesho sales file: {sales_file.name}, size: {sales_file.size}")
            debug_print(f"Uploaded Meesho returns file: {returns_file.name}, size: {returns_file.size}")
            
            # Check file extensions
            sales_ext = os.path.splitext(sales_file.name)[1].lower()
            returns_ext = os.path.splitext(returns_file.name)[1].lower()
            
            if sales_ext not in ['.csv', '.xlsx', '.xls'] or returns_ext not in ['.csv', '.xlsx', '.xls']:
                debug_print(f"❌ Unsupported file format: {sales_ext} or {returns_ext}")
                return Response({
                    "error": "Unsupported file format. Please upload CSV or Excel files for both sales and returns data."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process both files
            try:
                # Read sales file
                df_sales = self._read_file_to_dataframe(sales_file)
                if df_sales is None or df_sales.empty:
                    return Response({
                        "error": "Sales file contains no data or is in an unsupported format."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Read returns file
                df_returns = self._read_file_to_dataframe(returns_file)
                if df_returns is None or df_returns.empty:
                    return Response({
                        "error": "Returns file contains no data or is in an unsupported format."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                debug_print(f"Sales file shape: {df_sales.shape}")
                debug_print(f"Returns file shape: {df_returns.shape}")
                
                # Validate that the returns file has a cancel_return_date column
                returns_columns = set(df_returns.columns)
                sales_columns = set(df_sales.columns)
                
                # Check if 'cancel_return_date' column exists in returns dataset
                cancel_return_col = None
                for col in returns_columns:
                    if 'cancel' in str(col).lower() and 'return' in str(col).lower() and 'date' in str(col).lower():
                        cancel_return_col = col
                        break
                
                if not cancel_return_col:
                    # Try to find any column that might be the cancel/return date
                    for col in returns_columns:
                        if col not in sales_columns and ('cancel' in str(col).lower() or 'return' in str(col).lower()):
                            cancel_return_col = col
                            debug_print(f"Using '{cancel_return_col}' as cancel/return date column")
                            break
                
                if not cancel_return_col:
                    debug_print("⚠️ Returns file does not have a 'cancel_return_date' column")
                    # If no specific cancel/return date column found, check if all other columns match
                    expected_columns = sales_columns - returns_columns
                    extra_columns = returns_columns - sales_columns
                    
                    if expected_columns or (len(extra_columns) != 1):
                        debug_print(f"❌ Column mismatch between files. Sales file has {len(expected_columns)} unique columns, Returns file has {len(extra_columns)} unique columns")
                        return Response({
                            "error": "The returns file should have the same columns as the sales file, plus a 'cancel_return_date' column."
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # If there's exactly one extra column in returns, use that as cancel_return_date
                    if len(extra_columns) == 1:
                        cancel_return_col = list(extra_columns)[0]
                        debug_print(f"Using extra column '{cancel_return_col}' as cancel_return_date")
                else:
                    debug_print(f"Found cancel/return date column: '{cancel_return_col}'")
                    # Validate that all other columns in the returns file match the sales file
                    expected_columns = sales_columns - returns_columns
                    extra_columns = returns_columns - sales_columns - {cancel_return_col}
                    
                    if expected_columns or extra_columns:
                        debug_print(f"❌ Column mismatch between files after accounting for '{cancel_return_col}'")
                        debug_print(f"Missing columns in returns file: {expected_columns}")
                        debug_print(f"Extra columns in returns file: {extra_columns}")
                        return Response({
                            "error": "The returns file should have the same columns as the sales file, plus a 'cancel_return_date' column."
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                # Map columns for both files
                sales_mapping = identify_columns_with_gemini(df_sales)
                returns_mapping = identify_columns_with_gemini(df_returns)
                
                # Debug column mappings
                debug_print("Column mapping (sales file):\n" + json.dumps(
                    {k: v for k, v in sales_mapping.items() if not k.startswith('_')}, 
                    indent=2
                ))
                debug_print("Column mapping (returns file):\n" + json.dumps(
                    {k: v for k, v in returns_mapping.items() if not k.startswith('_')}, 
                    indent=2
                ))
                
                # Validate column mappings compatibility
                diff_columns = []
                for key in sales_mapping:
                    if key.startswith('_'):  # Skip metadata fields
                        continue
                    
                    # Transaction type can differ between files (and should)
                    if key == 'transaction_type':
                        continue
                    
                    # Compare mapping values
                    if sales_mapping.get(key) != returns_mapping.get(key):
                        diff_columns.append(key)
                
                if diff_columns:
                    logger.warning(f"Column mapping differences detected in {len(diff_columns)} columns: {diff_columns}")
                    debug_print(f"⚠️ Different column mappings detected between files: {', '.join(diff_columns)}")
                
                # Add source type column to both dataframes
                df_sales['record_type'] = 'sale'
                df_returns['record_type'] = 'return'
                
                # Merge dataframes
                df_merged = pd.concat([df_sales, df_returns], ignore_index=True)
                
                # Debug merged dataframe
                debug_print(f"Merged dataframe shape: {df_merged.shape}")
                debug_print(f"Sample merged data:\n{df_merged.head().to_string()}")
                
                # Create merged column mapping (prefer sales mapping but include both transaction types)
                merged_mapping = sales_mapping.copy()
                
                # Add cancel_return_date to the merged mapping if it exists
                if cancel_return_col:
                    merged_mapping['cancel_return_date'] = cancel_return_col
                    debug_print(f"Added 'cancel_return_date' mapping to '{cancel_return_col}'")
                
                # IMPORTANT: Make sure record_type is used for filtering data
                if '__source_type__' in df_merged.columns:
                    df_merged['record_type'] = df_merged['__source_type__']
                    df_merged.drop('__source_type__', axis=1, inplace=True)
                    debug_print("Renamed '__source_type__' to 'record_type' to prevent frontend special handling")
                
                # Debug column mapping for final analysis
                debug_print(f"Column mapping:\n{json.dumps({k: v for k, v in merged_mapping.items() if not k.startswith('_')}, indent=2)}")
                
                # Use analyze_sales_data to match the process for other datasets
                debug_print("Running full sales analysis on merged data...")
                analysis_results = analyze_sales_data(df_merged, merged_mapping, platform_type="meesho")
                
                # Compute metrics on merged data (same as before for compatibility)
                metrics = compute_sales_metrics(df_merged, merged_mapping)
                
                # Prepare final response with debug information
                debug_print(f"✅ Analysis complete")
                
                # Include debug logs in the response
                debug_info = {
                    "platform": "meesho",
                    "merged_rows": len(df_merged),
                    "sales_rows": len(df_sales),
                    "returns_rows": len(df_returns),
                    "columns_mapped": {
                        k: v for k, v in merged_mapping.items() 
                        if not k.startswith('_') and v is not None
                    }
                }
                
                # Get collected debug logs if available
                if hasattr(debug_print, 'log_collection'):
                    debug_info['logs'] = debug_print.log_collection
                
                # Final metrics object with exactly the required 8 metrics (same as before)
                final_metrics = {
                    "total_sales": metrics.get("total_sales", 0),
                    "average_sales": metrics.get("average_sales", 0),
                    "return_rate": metrics.get("return_rate", 0),
                    "cancellation_rate": metrics.get("cancellation_rate", 0),
                    "total_return_amount": metrics.get("total_return_amount", 0),
                    "total_replacements": metrics.get("total_replacements", 0),
                    "total_regions": metrics.get("total_regions", 0),
                    "total_products": metrics.get("total_products", 0),
                    # CRITICAL CHANGE: Set data_source to a standard type instead of marking it as Meesho
                    # This will prevent the frontend from using special Meesho handling
                    "data_source": "standard",
                    # Include debug info but don't use a format that triggers Meesho-specific frontend code
                    "_debug": debug_info  # Use _debug instead of debug to prevent frontend detection
                }
                
                # Include full analysis results for the UI
                final_metrics.update(analysis_results)
                
                # Make sure all visualization data is included in the response
                if 'platform_specific' in analysis_results:
                    final_metrics["platform_specific"] = analysis_results["platform_specific"]
                    debug_print(f"Including platform-specific analysis with {len(analysis_results['platform_specific'])} metrics")
                
                # Ensure critical visualization fields are present before standardizing
                for key in ["time_series", "top_products", "top_regions", "sales_channels", "visualization_data", "order_metrics", "key_metrics"]:
                    if key in analysis_results:
                        final_metrics[key] = analysis_results[key]
                        debug_print(f"Including {key} for visualization")
                    else:
                        debug_print(f"Warning: {key} not found in analysis results")
                
                # Add standard field for transaction types if missing
                if "transaction_types" not in final_metrics and "order_metrics" in final_metrics:
                    final_metrics["transaction_types"] = [
                        {"name": "Regular Orders", "count": final_metrics["order_metrics"].get("regular_orders", 0)},
                        {"name": "Cancelled", "count": final_metrics["order_metrics"].get("cancelled_orders", 0)},
                        {"name": "Returned", "count": final_metrics["order_metrics"].get("returned_orders", 0)},
                        {"name": "Replaced", "count": final_metrics["order_metrics"].get("replaced_orders", 0)}
                    ]
                    debug_print("Added transaction_types field to match standard dataset structure")
                
                # Ensure the merged dataset has standard format
                if "_source_type__" in merged_mapping:
                    del merged_mapping["_source_type__"]
                if "cancel_return_date" in merged_mapping:
                    del merged_mapping["cancel_return_date"]
                
                # Remove any property in final_metrics that identifies it as Meesho data
                keys_to_remove = []
                for key in final_metrics:
                    if isinstance(key, str) and ("meesho" in key.lower() or "debug" in key.lower()):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del final_metrics[key]
                
                # Make sure metrics are in the expected format for chart rendering
                if "top_products" in final_metrics and len(final_metrics["top_products"]) > 0:
                    for product in final_metrics["top_products"]:
                        if "percentage" not in product and "value" in product:
                            product["percentage"] = 0  # Add missing percentage field
                
                if "top_regions" in final_metrics and len(final_metrics["top_regions"]) > 0:
                    for region in final_metrics["top_regions"]:
                        if "percentage" not in region and "value" in region:
                            region["percentage"] = 0  # Add missing percentage field
                
                # CRITICAL CHANGE: Format the response exactly like non-Meesho datasets
                # This is the key to preventing frontend recalculation
                standardized_response = {
                    "success": True,
                    "message": "File uploaded and analyzed successfully",
                    "file_id": "standard_data_file",  # Generic ID, not meesho-specific
                    "analysis_id": "standard_analysis",  # Generic ID, not meesho-specific
                    "platform_type": None,  # Don't specify any platform type to prevent special handling
                    "analysis": final_metrics,  # Put all metrics inside the analysis field like other datasets
                    "column_mapping": merged_mapping  # Include column mapping
                }
                
                # Include debug info in a standard format
                if hasattr(debug_print, 'log_collection'):
                    # Filter out any mentions of "Meesho" from the logs to prevent frontend detection
                    filtered_logs = []
                    for log in debug_print.log_collection:
                        # Replace any mention of Meesho with "Dataset" to prevent triggering frontend-specific code
                        filtered_log = log.replace("Meesho", "Dataset").replace("meesho", "dataset")
                        filtered_logs.append(filtered_log)
                    standardized_response["debug_logs"] = filtered_logs
                
                # Set calculated flags to ensure frontend doesn't recalculate
                if "analysis" in standardized_response and isinstance(standardized_response["analysis"], dict):
                    standardized_response["analysis"]["_is_backend_calculated"] = True
                    standardized_response["analysis"]["_skip_frontend_processing"] = True
                
                # Debug print the response status
                debug_print(f"Sending standardized response to match other datasets")
                
                return Response(standardized_response, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error processing Meesho files: {str(e)}")
                logger.error(traceback.format_exc())
                debug_print(f"❌ Error processing Meesho files: {str(e)}")
                return Response({
                    "error": f"Error processing Meesho files: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            logger.error(f"Unexpected error in Meesho handler: {str(e)}")
            logger.error(traceback.format_exc())
            debug_print(f"❌ Unexpected error in Meesho handler: {str(e)}")
            return Response({
                "error": f"Unexpected error in Meesho handler: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _read_file_to_dataframe(self, file_obj):
        """Helper method to read a file into a pandas DataFrame"""
        try:
            file_name = file_obj.name
            file_extension = os.path.splitext(file_name)[1].lower()
            
            # Save the file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in file_obj.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            logger.info(f"Saved file temporarily to: {temp_file_path}")
            
            # Determine the file type and read accordingly
            df = None
            if file_extension == '.csv':
                # Use the same CSV reading logic from the upload view
                with open(temp_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    sample = f.read(4096)
                
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample)
                    detected_delimiter = dialect.delimiter
                    logger.info(f"Detected delimiter: '{detected_delimiter}'")
                except:
                    detected_delimiter = ','
                    logger.warning("Failed to detect delimiter, defaulting to comma")
                
                try:
                    has_header = sniffer.has_header(sample)
                except:
                    has_header = True
                
                # Try with detected settings
                try:
                    df = pd.read_csv(
                        temp_file_path, 
                        delimiter=detected_delimiter,
                        header=0 if has_header else None,
                        encoding='utf-8',
                        low_memory=False,
                        on_bad_lines='skip'
                    )
                except Exception as e:
                    logger.error(f"First attempt to read CSV failed: {e}")
                    
                    # Try with different encoding
                    df = pd.read_csv(
                        temp_file_path,
                        delimiter=detected_delimiter,
                        header=0 if has_header else None,
                        encoding='latin1',
                        low_memory=False,
                        on_bad_lines='skip'
                    )
                
                # Try alternative delimiters if needed
                if df.shape[1] == 1:
                    for delimiter in [';', '\t', '|']:
                        try:
                            temp_df = pd.read_csv(
                                temp_file_path,
                                delimiter=delimiter,
                                header=0 if has_header else None,
                                encoding='utf-8',
                                low_memory=False,
                                on_bad_lines='skip'
                            )
                            if temp_df.shape[1] > 1:
                                df = temp_df
                                break
                        except:
                            pass
            
            elif file_extension in ['.xlsx', '.xls']:
                # Read Excel file
                try:
                    df = pd.read_excel(temp_file_path, engine='openpyxl')
                except:
                    # Fallback to xlrd for older Excel files
                    df = pd.read_excel(temp_file_path, engine='xlrd')
            
            # Clean up the temp file
            try:
                os.unlink(temp_file_path)
            except:
                logger.warning(f"Failed to delete temporary file: {temp_file_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading file to DataFrame: {str(e)}")
            logger.error(traceback.format_exc())
            return None