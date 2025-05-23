from django.views.generic import TemplateView
from django.http import JsonResponse
from .models import Category, SubCategory, FeeStructure, AmazonProgram
from decimal import Decimal

class FeeCalculatorView(TemplateView):
    template_name = 'fee_calculator/calculator.html'

    def calculate_closing_fee(self, selling_price, program_name):
        """
        Calculate the fixed closing fee based on price ranges and program
        
        Args:
            selling_price (float): The selling price of the item
            program_name (str): The name of the Amazon program
            
        Returns:
            float: The fixed closing fee amount
        """
        print(f"Calculating closing fee for selling price: {selling_price} and program: {program_name}")
        selling_price = float(selling_price)
        
        if program_name == 'FBA':
            # Get subcategory from program name
            subcategory = SubCategory.objects.get(id=self.request.POST.get('subcategory'))
            if subcategory.is_exception:
                if selling_price >= 0 and selling_price <= 500:
                    fee = 12.0
                elif selling_price >= 501 and selling_price <= 1000:
                    fee = 25.0
                else:
                    fee = 50.0
            else:
                if selling_price >= 0 and selling_price <= 250:
                    fee = 25.0
                elif selling_price >= 251 and selling_price <= 500:
                    fee = 20.0
                elif selling_price >= 501 and selling_price <= 1000:
                    fee = 25.0
                else:
                    fee = 50.0
        elif program_name == 'SELLER_FLEX':
            if selling_price >= 0 and selling_price <= 250:
                fee = 7.0
            elif selling_price >= 251 and selling_price <= 500:
                fee = 11.0
            elif selling_price >= 501 and selling_price <= 1000:
                fee = 30.0
            else:
                fee = 61.0
        else:
            if selling_price >= 0 and selling_price <= 250:
                fee = 4.0
            elif selling_price >= 251 and selling_price <= 500:
                fee = 9.0
            elif selling_price >= 501 and selling_price <= 1000:
                fee = 30.0
            else:
                fee = 61.0
            
        print(f"Closing fee: {fee}")
        return fee

    def calculate_referral_fee(self, category_id, subcategory_id, selling_price):
        print(f"Calculating referral fee for category {category_id}, subcategory {subcategory_id}, selling price {selling_price}")
        # Get all fee structures for this category and subcategory
        fee_structures = FeeStructure.objects.filter(
            category_id=category_id,
            subcategory_id=subcategory_id
        )
        
        print(f"Found {fee_structures.count()} fee structures")
        
        # If no fee structure found, return 0
        if not fee_structures.exists():
            print("No fee structures found, returning 0")
            return 0
            
        # Convert selling price to Decimal for accurate comparison
        selling_price = Decimal(str(selling_price))
        
        # Sort fee structures based on their conditions
        # For 'gt'/'gte', sort by value in descending order
        # For 'lt'/'lte', sort by value in ascending order
        gt_structures = []
        lt_structures = []
        eq_structures = []
        
        for fs in fee_structures:
            if fs.condition in ['gt', 'gte']:
                gt_structures.append(fs)
            elif fs.condition in ['lt', 'lte']:
                lt_structures.append(fs)
            elif fs.condition == 'eq':
                eq_structures.append(fs)
        
        # Sort the lists
        gt_structures.sort(key=lambda x: x.value, reverse=True)  # Descending
        lt_structures.sort(key=lambda x: x.value)  # Ascending
        
        # Combine the sorted lists with eq_structures in the middle
        sorted_structures = gt_structures + eq_structures + lt_structures
        
        # Check each fee structure
        for fee_structure in sorted_structures:
            value = fee_structure.value
            condition = fee_structure.condition
            
            print(f"Checking fee structure: value={value}, condition={condition}")
            
            # Skip if no condition/value set
            if not condition or value is None:
                print("Skipping fee structure - no condition/value set")
                continue
                
            # Check the condition
            condition_met = False
            if condition == 'gte' and selling_price >= value:
                condition_met = True
            elif condition == 'lte' and selling_price <= value:
                condition_met = True
            elif condition == 'eq' and selling_price == value:
                condition_met = True
            elif condition == 'gt' and selling_price > value:
                condition_met = True
            elif condition == 'lt' and selling_price < value:
                condition_met = True
                
            print(f"Condition met: {condition_met}")
                
            # If condition is met, calculate referral fee
            if condition_met:
                fee = float(selling_price * fee_structure.referral_fee_percentage / 100)
                print(f"Returning referral fee: {fee}")
                return fee
                
        # If no matching condition found, use the first fee structure
        fee = float(selling_price * sorted_structures[0].referral_fee_percentage / 100)
        print(f"No matching conditions, using first fee structure. Fee: {fee}")
        return fee

    def calculate_easy_ship_local_fee(self, weight_in_g, dimensions):
        print(f"Calculating Easy Ship local fee for weight {weight_in_g}g and dimensions {dimensions}")
        # Calculate volumetric weight
        volume = dimensions['length'] * dimensions['width'] * dimensions['height']
        volumetric_weight = (volume / 5000) * 1000
        
        # Use higher of actual vs volumetric weight in grams
        chargeable_weight = max(weight_in_g, volumetric_weight)
        print(f"Chargeable weight (higher of actual {weight_in_g}g vs volumetric {volumetric_weight}g): {chargeable_weight}g")
        
        # Base fee for 0-500g
        if chargeable_weight <= 500:
            return 43
        
        # 501-1000g
        if chargeable_weight <= 1000:
            return 43 + 13
        
        # 1001g to 5000g: Base + 13 + 21 for each 1000g bracket
        if chargeable_weight <= 5000:
            additional_brackets = ((chargeable_weight - 1000) // 1000) + 1
            return 43 + 13 + (21 * additional_brackets)
        
        # 5001g onwards: Base + 13 + (21 * 4) + 12 for each additional 1000g bracket
        additional_brackets = ((chargeable_weight - 5000) // 1000) + 1
        return 43 + 13 + (21 * 4) + (12 * additional_brackets)

    def calculate_easy_ship_national_fee(self, weight_in_g, dimensions):
        print(f"Calculating Easy Ship national fee for weight {weight_in_g}g and dimensions {dimensions}")
        # Calculate volumetric weight
        volume = dimensions['length'] * dimensions['width'] * dimensions['height']
        volumetric_weight = (volume / 5000) * 1000
        
        # Use higher of actual vs volumetric weight in grams
        chargeable_weight = max(weight_in_g, volumetric_weight)
        print(f"Chargeable weight (higher of actual {weight_in_g}g vs volumetric {volumetric_weight}g): {chargeable_weight}g")
        
        # Base fee for 0-500g
        if chargeable_weight <= 500:
            return 76
        
        # 501-1000g
        if chargeable_weight <= 1000:
            return 76 + 25
        
        # 1001g to 5000g: Base + 25 + 33 for each 1000g bracket
        if chargeable_weight <= 5000:
            additional_brackets = ((chargeable_weight - 1000) // 1000) + 1
            return 76 + 25 + (33 * additional_brackets)
        
        # 5001g onwards: Base + 25 + (33 * 4) + 16 for each additional 1000g bracket
        additional_brackets = ((chargeable_weight - 5000) // 1000) + 1
        return 76 + 25 + (33 * 4) + (16 * additional_brackets)

    def calculate_fba_local_fee(self, weight_in_g, dimensions):
        print(f"Calculating FBA local fee for weight {weight_in_g}g and dimensions {dimensions}")
        # Calculate volumetric weight
        volume = dimensions['length'] * dimensions['width'] * dimensions['height']
        volumetric_weight = (volume / 5000) * 1000
        
        # Use higher of actual vs volumetric weight in grams
        chargeable_weight = max(weight_in_g, volumetric_weight)
        
        # Base fee (including Pick & Pack Fee of Rs. 14)
        if chargeable_weight <= 500:
            return 29 + 14
        
        # 501-1000g
        if chargeable_weight <= 1000:
            return 29 + 14 + 13
        
        # 1001g to 5000g: Base + 13 + 21 for each 1000g bracket
        if chargeable_weight <= 5000:
            additional_brackets = ((chargeable_weight - 1000) // 1000) + 1
            return 29 + 14 + 13 + (21 * additional_brackets)
        
        # 5001g onwards: Base + 13 + (21 * 4) + 12 for each additional 1000g bracket
        additional_brackets = ((chargeable_weight - 5000) // 1000) + 1
        return 29 + 14 + 13 + (21 * 4) + (12 * additional_brackets)

    def calculate_fba_national_fee(self, weight_in_g, dimensions):
        print(f"Calculating FBA national fee for weight {weight_in_g}g and dimensions {dimensions}")
        # Calculate volumetric weight
        volume = dimensions['length'] * dimensions['width'] * dimensions['height']
        volumetric_weight = (volume / 5000) * 1000
        
        chargeable_weight = max(weight_in_g, volumetric_weight)
        
        # Base fee (including Pick & Pack Fee of Rs. 14)
        if chargeable_weight <= 500:
            return 62 + 14
        
        # 501-1000g
        if chargeable_weight <= 1000:
            return 62 + 14 + 25
        
        # 1001g to 5000g: Base + 25 + 33 for each 1000g bracket
        if chargeable_weight <= 5000:
            additional_brackets = ((chargeable_weight - 1000) // 1000) + 1
            return 62 + 14 + 25 + (33 * additional_brackets)
        
        # 5001g onwards: Base + 25 + (33 * 4) + 16 for each additional 1000g bracket
        additional_brackets = ((chargeable_weight - 5000) // 1000) + 1
        return 62 + 14 + 25 + (33 * 4) + (16 * additional_brackets)

    def calculate_seller_flex_local_fee(self, weight_in_g, dimensions):
        print(f"Calculating Seller Flex local fee for weight {weight_in_g}g and dimensions {dimensions}")
        # Calculate volumetric weight
        volume = dimensions['length'] * dimensions['width'] * dimensions['height']
        volumetric_weight = (volume / 5000) * 1000
        
        # Use higher of actual vs volumetric weight in grams
        chargeable_weight = max(weight_in_g, volumetric_weight)
        print(f"Chargeable weight (higher of actual {weight_in_g}g vs volumetric {volumetric_weight}g): {chargeable_weight}g")
        
        # Base fee (including Technology Fee of Rs. 14)
        if chargeable_weight <= 500:
            return 29 + 14
        
        # 501-1000g
        if chargeable_weight <= 1000:
            return 29 + 14 + 13
        
        # 1001g to 5000g: Base + 13 + 21 for each 1000g bracket
        if chargeable_weight <= 5000:
            additional_brackets = ((chargeable_weight - 1000) // 1000) + 1
            return 29 + 14 + 13 + (21 * additional_brackets)
        
        # 5001g onwards: Base + 13 + (21 * 4) + 12 for each additional 1000g bracket
        additional_brackets = ((chargeable_weight - 5000) // 1000) + 1
        return 29 + 14 + 13 + (21 * 4) + (12 * additional_brackets)

    def calculate_seller_flex_national_fee(self, weight_in_g, dimensions):
        print(f"Calculating Seller Flex national fee for weight {weight_in_g}g and dimensions {dimensions}")
        # Calculate volumetric weight
        volume = dimensions['length'] * dimensions['width'] * dimensions['height']
        volumetric_weight = (volume / 5000) * 1000
        
        # Use higher of actual vs volumetric weight in grams
        chargeable_weight = max(weight_in_g, volumetric_weight)
        print(f"Chargeable weight (higher of actual {weight_in_g}g vs volumetric {volumetric_weight}g): {chargeable_weight}g")
        
        # Base fee (including Technology Fee of Rs. 14)
        if chargeable_weight <= 500:
            return 62 + 14
        
        # 501-1000g
        if chargeable_weight <= 1000:
            return 62 + 14 + 25
        
        # 1001g to 5000g: Base + 25 + 33 for each 1000g bracket
        if chargeable_weight <= 5000:
            additional_brackets = ((chargeable_weight - 1000) // 1000) + 1
            return 62 + 14 + 25 + (33 * additional_brackets)
        
        # 5001g onwards: Base + 25 + (33 * 4) + 16 for each additional 1000g bracket
        additional_brackets = ((chargeable_weight - 5000) // 1000) + 1
        return 62 + 14 + 25 + (33 * 4) + (16 * additional_brackets)

    def post(self, request, *args, **kwargs):
        try:
            print("Processing POST request")
            # Get and validate input parameters
            selling_price = Decimal(request.POST.get('selling_price', 0))
            product_cost = Decimal(request.POST.get('product_cost', 0))
            category_id = request.POST.get('category')
            gst_percentage = Decimal(request.POST.get('gst', 0))
            subcategory_id = request.POST.get('subcategory')
            weight = float(request.POST.get('weight', 0))  # Weight in grams
            misc_cost = float(request.POST.get('miscCost', 0))
            
            print(f"Input parameters: selling_price={selling_price}, product_cost={product_cost}, category={category_id}, gst={gst_percentage}, subcategory={subcategory_id}, weight={weight}, misc_cost={misc_cost}")
            
            dimensions = {
                'length': float(request.POST.get('length', 0)),
                'width': float(request.POST.get('width', 0)), 
                'height': float(request.POST.get('height', 0))
            }
            
            print(f"Product dimensions: {dimensions}")

            # Validate required fields
            if not all([selling_price, category_id, subcategory_id, weight]):
                print("Missing required fields")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing required fields',
                    'data': None
                }, status=400)

            # Calculate GST amount
            gst_amount = round((selling_price - (selling_price * 100) / (Decimal('100') + gst_percentage)),2)
            print(f"Calculated GST amount: {gst_amount}")

            # Get Amazon programs
            amazon_programs = AmazonProgram.objects.all()
            print(f"Found {amazon_programs.count()} Amazon programs")

            if not amazon_programs.exists():
                print("No Amazon programs found")
                return JsonResponse({
                    'status': 'error', 
                    'message': 'No Amazon programs found',
                    'data': None
                }, status=404)

            results = {
                'selling_price': float(selling_price),
                'product_cost': float(product_cost),
                'gst_percentage': float(gst_percentage),
                'gst_amount': float(gst_amount),
                'misc_cost': float(misc_cost),
                'weight': weight,
                'dimensions': dimensions,
                'programs': {}
            }

            # Calculate shipping fees for each location and program
            location_fees = {
                'EASY_SHIP': {
                    'local': self.calculate_easy_ship_local_fee(weight, dimensions),
                    'regional': (self.calculate_easy_ship_local_fee(weight, dimensions) + self.calculate_easy_ship_national_fee(weight, dimensions)) / 2,
                    'national': self.calculate_easy_ship_national_fee(weight, dimensions)
                },
                'FBA': {
                    'local': self.calculate_fba_local_fee(weight, dimensions),
                    'regional': (self.calculate_fba_local_fee(weight, dimensions) + self.calculate_fba_national_fee(weight, dimensions)) / 2,
                    'national': self.calculate_fba_national_fee(weight, dimensions)
                },
                'SELLER_FLEX': {
                    'local': self.calculate_seller_flex_local_fee(weight, dimensions),
                    'regional': (self.calculate_seller_flex_local_fee(weight, dimensions) + self.calculate_seller_flex_national_fee(weight, dimensions)) / 2,
                    'national': self.calculate_seller_flex_national_fee(weight, dimensions)
                }
            }
            
            print(f"Calculated location fees: {location_fees}")

            # Calculate referral fee
            referral_fee = self.calculate_referral_fee(category_id, subcategory_id, selling_price)
            print(f"Calculated referral fee: {referral_fee}")

            # Calculate fees and profits for each program
            for program in amazon_programs:
                print(f"\nProcessing program: {program.name}")
                program_name = program.name
                    
                # Calculate closing fee based on program
                closing_fee = self.calculate_closing_fee(selling_price, program_name)
                print(f"Closing fee: {closing_fee}")
                
                base_fees = Decimal(str(referral_fee)) + Decimal(str(closing_fee)) + gst_amount + Decimal(str(misc_cost))
                print(f"Base fees for {program_name}: {base_fees}")

                program_results = {
                    'referral_fee': float(referral_fee),
                    'closing_fee': float(closing_fee),
                    'locations': {}
                }

                # Calculate for each location
                if program_name in location_fees:
                    for location, shipping_fee in location_fees[program_name].items():
                        print(f"Calculating for location: {location}")
                        total_fees = base_fees + Decimal(str(shipping_fee))
                        net_amount = selling_price - total_fees - product_cost
                        profit = net_amount
                        
                        print(f"Total fees: {total_fees}, Net amount: {net_amount}, Profit: {profit}")
                        
                        program_results['locations'][location] = {
                            'shipping_fee': shipping_fee,
                            'total_fees': float(total_fees),
                            'net_amount': float(net_amount),
                            'profit': float(profit),
                            'profit_margin': float((profit / selling_price) * 100) if selling_price else 0
                        }

                    # Calculate average values
                    shipping_fees = [loc['shipping_fee'] for loc in program_results['locations'].values()]
                    total_fees = [loc['total_fees'] for loc in program_results['locations'].values()]
                    net_amounts = [loc['net_amount'] for loc in program_results['locations'].values()]
                    profits = [loc['profit'] for loc in program_results['locations'].values()]
                    profit_margins = [loc['profit_margin'] for loc in program_results['locations'].values()]
                    
                    print(f"Calculating averages for {program_name}")

                    program_results['locations']['average'] = {
                        'shipping_fee': sum(shipping_fees) / len(shipping_fees),
                        'total_fees': sum(total_fees) / len(total_fees),
                        'net_amount': sum(net_amounts) / len(net_amounts),
                        'profit': sum(profits) / len(profits),
                        'profit_margin': sum(profit_margins) / len(profit_margins)
                    }

                results['programs'][program_name] = program_results

            print("Calculations completed successfully")
            return JsonResponse({
                'status': 'success',
                'message': 'Calculations completed successfully',
                'data': results
            })

        except (ValueError, TypeError) as e:
            print(f"Invalid input error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid input: {str(e)}',
                'data': None
            }, status=400)
        except Exception as e:
            print(f"Server error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Server error: {str(e)}',
                'data': None
            }, status=500)

    def get_context_data(self, **kwargs):
        print("Getting context data")
        context = super().get_context_data(**kwargs)
        # Get all categories with their related subcategories
        # Get categories that have fee structures
        categories_with_fees = Category.objects.filter(
            id__in=FeeStructure.objects.values('category_id').distinct()
        )
        
        print(f"Found {categories_with_fees.count()} categories with fee structures")

        # For each category, get its subcategories that have fee structures
        categories_with_subcats = {}
        for category in categories_with_fees:
            subcategories = SubCategory.objects.filter(
                category=category
            ).distinct()
            categories_with_subcats[category] = subcategories
            print(f"Category {category.name} has {subcategories.count()} subcategories")

        context['categories_with_subcats'] = categories_with_subcats
        context['fee_structures'] = FeeStructure.objects.all()
        context['categories'] = Category.objects.all()
        context['subcategories'] = SubCategory.objects.all()
        context['amazon_programs'] = AmazonProgram.objects.all()
        
        print("Context data prepared successfully")
        return context

    """
    Fee Calculation Summary:
    
    1. Easy Ship Program:
       - Local: Base fee (Rs. 43) + additional charges based on weight brackets
       - National: Base fee (Rs. 76) + additional charges based on weight brackets
       - Regional: Average of local and national fees
    
    2. FBA (Fulfillment by Amazon) Program:
       - Local: Base fee (Rs. 29) + Pick & Pack fee (Rs. 14) + additional charges based on weight brackets
       - National: Base fee (Rs. 62) + Pick & Pack fee (Rs. 14) + additional charges based on weight brackets
       - Regional: Average of local and national fees
    
    3. Seller Flex Program:
       - Local: Base fee (Rs. 29) + Technology fee (Rs. 14) + additional charges based on weight brackets
       - National: Base fee (Rs. 62) + Technology fee (Rs. 14) + additional charges based on weight brackets
       - Regional: Average of local and national fees
    
    Common calculations for all programs:
    - Referral Fee: Based on category and subcategory fee structures
    - Closing Fee: Based on selling price ranges and program type
    - GST: Calculated based on provided GST percentage
    - Total Fees = Base fees + Shipping fees + GST + Misc costs
    - Net Amount = Selling Price - Total Fees - Product Cost
    - Profit = Net Amount
    - Profit Margin = (Profit / Selling Price) * 100
    """
