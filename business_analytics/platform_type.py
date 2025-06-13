platform_charts_to_display = {
    "Amazon": [
    # //   Sum of all sales marked as B2B from order records
      "B2B Sales",
  
      # // Sum of all sales marked as B2C from order records
      "B2C Sales",
  
      # // Total of B2B + B2C sales (revenue before returns/refunds)
      "Total Sales",
  
      # // Count of orders with status = 'Cancelled'
      "Total Cancelled Orders",
  
      # // Sum of order values where status = 'Cancelled'
      "Cancelled Value",
  
      # // Count of orders where 'replacement_order_id' or 'is_replacement' = true
      "Total Replacements",
  
      # // Sum of values of original items replaced (can include logistic cost too)
      "Replacement Value",
  
      # // Count of orders with status = 'Refunded'
      "Total Refunded Orders",
  
      # // Total refunded monetary value from those orders
      "Refunded Value",
  
      # // Total number of orders regardless of status (excluding cancellations if needed)
      "Number of Total Orders",
  
      # // Total quantity of items sold (sum of quantity column across all orders)
      "Number of Units",
  
      # // State with the highest total sales volume or order count
      "Top Selling State",
  
      # // State with the lowest total sales volume or order count
      "Low Selling State",
  
      # // Top 5 SKUs ranked by total quantity sold or total sales amount
      "Top 5 Selling SKU",
  
      # // Bottom 5 SKUs ranked by total quantity sold (excluding zero sales if desired)
      "Lowest 5 Selling SKU"
    ],
  
    "Amazon B2B": [
      # // Total B2B sales from GST reports
      "B2B Sales",
  
      # // Count of orders with Transaction Type = 'Shipment'
      "Shipped Orders",
  
      # // Count of orders with Transaction Type = 'Cancel'
      "Cancelled Orders",
  
      # // Total value of cancelled orders
      "Cancelled Value",
  
      # // Count of orders with Transaction Type = 'Refund'
      "Refunded Orders",
  
      # // Total value of refunded orders
      "Refund Value",
  
      # // Total tax amount collected (GST, IGST, etc.)
      "Total Tax Amount",
      
      # // Tax as percentage of total sales
      "Tax Percentage",
  
      # // Distribution of orders by fulfillment channel
      "Fulfillment Channels",
  
      # // Top 10 states by sales value
      "Top Selling States",
  
      # // Distribution of transactions by type (Shipment/Cancel/Refund)
      "Transaction Types",
      
      # // Distribution of sales by type (Shipment/Cancel/Refund)
      "Transaction Values"
    ],
  
    "Meesho": [
      # // Total sales value from Meesho orders (after or before discounts)
      "Total Sales",
  
      # // Count of orders marked as 'Returned'
      "Total Returns",
  
      # // Sum of refunded values for all returned orders
      "Returns Value",
  
      # // Total number of Meesho orders placed
      "Number of Total Orders",
  
      # // Total quantity of products sold via Meesho
      "Number of Units",
  
      # // State where Meesho had the most orders or revenue
      "Top Selling State",
  
      # // State where Meesho had the least orders or revenue
      "Low Selling State",
  
      # // Top 5 Meesho SKUs based on quantity or sales
      "Top 5 Selling SKU",
  
      # // Bottom 5 SKUs sold via Meesho based on sales volume
      "Lowest 5 Selling SKU"
    ],
  
    "Flipkart": [
      # // Sum of all revenue generated from Flipkart orders
      "Total Sales Revenue",
  
      # // Count of orders returned via Flipkart
      "Total Returns",
  
      # // Total value refunded due to returns
      "Returns Revenue",
  
      # // Total number of orders placed on Flipkart
      "Number of Total Orders",
  
      # // Total number of product units sold on Flipkart
      "Number of Units",
  
      # // State with highest Flipkart sales or order count
      "Top Selling State",
  
      # // State with lowest Flipkart sales or order count
      "Low Selling State",
  
      # // Top 5 Flipkart SKUs by revenue or quantity sold
      "Top 5 Selling SKU",
  
      # `// Lowest 5 SKUs by revenue or quantity sold on Flipkart
      "Lowest 5 Selling SKU"
    ]
  }
  