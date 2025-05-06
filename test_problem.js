// Test script to simulate the original problem with JSON parsing at position 34879
console.log("==============================================");
console.log("TESTING ORIGINAL PROBLEM SCENARIO");
console.log("==============================================");

// Import the fixBrokenJSON function from our test
function fixBrokenJSON(text) {
    console.log('Attempting to fix JSON data of length:', text.length);
    
    // Special handling for analysis_option field issues
    if (text.includes('"analysis_option":')) {
        console.log('Found analysis_option field, checking for issues...');
        
        // Fix pattern for option with numeric value - properly quote the value
        const basicPattern = /"analysis_option"\s*:\s*(\d+)([,}])/g;
        if (text.match(basicPattern)) {
            console.log('Found unquoted analysis_option value, fixing');
            text = text.replace(basicPattern, '"analysis_option":"$1"$2');
        }
        
        // Fix pattern for option with an extra quote after the number
        const brokenPattern = /"analysis_option"\s*:\s*(\d+)"\s*,/g;
        if (text.match(brokenPattern)) {
            console.log('Found analysis_option field with extra quote, fixing');
            text = text.replace(brokenPattern, '"analysis_option":"$1",');
        }
        
        // Fix pattern for option with quotes on wrong side
        const wrongQuotePattern = /"analysis_option"\s*:\s*"(\d+)([,}])/g;
        if (text.match(wrongQuotePattern)) {
            console.log('Found analysis_option with misplaced quotes, fixing');
            text = text.replace(wrongQuotePattern, '"analysis_option":"$1"$2');
        }
    }
    
    // Generic option field fixes
    if (text.includes('"option":')) {
        console.log('Found option field, checking for issues...');
        
        // Fix pattern for option with numeric value - properly quote the value
        const basicPattern = /"option"\s*:\s*(\d+)([,}])/g;
        if (text.match(basicPattern)) {
            console.log('Found unquoted option value, fixing');
            text = text.replace(basicPattern, '"option":"$1"$2');
        }
        
        // Fix pattern for option with an extra quote after the number (position 34879 issue)
        const brokenPattern = /"option"\s*:\s*(\d+)"\s*,/g;
        if (text.match(brokenPattern)) {
            console.log('Found option field with extra quote, fixing');
            text = text.replace(brokenPattern, '"option":"$1",');
        }
        
        // Fix pattern for option with quotes on wrong side
        const wrongQuotePattern = /"option"\s*:\s*"(\d+)([,}])/g;
        if (text.match(wrongQuotePattern)) {
            console.log('Found option with misplaced quotes, fixing');
            text = text.replace(wrongQuotePattern, '"option":"$1"$2');
        }
    }
    
    // Apply additional fixes to handle common JSON issues
    const cleanText = text
        // Remove control characters 
        .replace(/[\x00-\x1F\x7F]/g, '')
        // Fix unescaped backslashes in strings
        .replace(/([^\\])\\([^\\/"bfnrtu])/g, '$1\\\\$2')
        // Fix trailing commas in arrays and objects
        .replace(/,\s*}/g, '}')
        .replace(/,\s*\]/g, ']')
        // Fix missing quotes around property names
        .replace(/([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)/g, '$1"$2"$3')
        // Fix broken quotes in option values - recurring theme
        .replace(/"analysis_option"\s*:\s*(\d+)([,}])/g, '"analysis_option":"$1"$2')
        .replace(/"analysis_option"\s*:\s*(\d+)"\s*,/g, '"analysis_option":"$1",')
        .replace(/"option"\s*:\s*(\d+)([,}])/g, '"option":"$1"$2')
        .replace(/"option"\s*:\s*(\d+)"\s*,/g, '"option":"$1",');
    
    // Manual fix for specific broken pattern
    // Handle the case where there's an extra quote directly 
    const specificFix = text.replace(/"analysis_option"\s*:\s*(\d+)"\s*,/g, '"analysis_option":"$1",');
    if (specificFix !== text) {
        console.log('Applied specific fix for analysis_option field');
        return specificFix;
    }
    
    // Return the cleaned text
    return cleanText;
}

// Create a simple test case with just the problematic pattern
const simpleTest = '{"data":{"metadata":{"analysis_option":1","time_range":"30d"}}}';
console.log("Simple test JSON:", simpleTest);

// Try to parse the problematic JSON (should fail)
try {
    const data = JSON.parse(simpleTest);
    console.log("UNEXPECTED: Simple test JSON parsed without errors!");
} catch (error) {
    console.log("Expected parse error:", error.message);
    
    // Check if the error message mentions the expected position
    const positionMatch = error.message.match(/position (\d+)/);
    if (positionMatch) {
        const errorPosition = parseInt(positionMatch[1]);
        console.log(`Error at position ${errorPosition}`);
        
        // Show context around error position
        const errorContextStart = Math.max(0, errorPosition - 10);
        const errorContextEnd = Math.min(simpleTest.length, errorPosition + 10);
        console.log(`Context around error: "${simpleTest.substring(errorContextStart, errorContextEnd)}"`);
    }
}

// Now fix the JSON with our function
const fixedJSON = fixBrokenJSON(simpleTest);
console.log("\nFixed JSON with our repair function:", fixedJSON);

// Try to parse the fixed JSON
try {
    const data = JSON.parse(fixedJSON);
    console.log("✓ Fixed JSON parses correctly!");
    console.log("Option value:", data.data.metadata.analysis_option);
} catch (fixError) {
    console.log("✗ Fixed JSON still fails:", fixError.message);
}

// Second test with complete problematic JSON
console.log("\n==============================================");
console.log("SECOND TEST: COMPLETE RESPONSE");
console.log("==============================================");

// Function to generate a more valid problematic JSON string
function generateProperJSON() {
    // Create a short but proper JSON with the broken analysis_option field
    return `{
        "status": "success",
        "data": {
            "time_series": [
                {"date": "2023-01-01", "value": 100},
                {"date": "2023-01-02", "value": 200}
            ],
            "metadata": {
                "analysis_option":1",
                "time_range": "30d",
                "segments": []
            }
        }
    }`;
}

const properJSON = generateProperJSON();
console.log("Generated JSON with broken analysis_option:");
console.log(properJSON);

// Try to parse
try {
    const data = JSON.parse(properJSON);
    console.log("UNEXPECTED: JSON parsed without errors!");
} catch (error) {
    console.log("Expected parse error:", error.message);
    
    // Now apply our fix
    const fixedProperJSON = fixBrokenJSON(properJSON);
    console.log("\nFixed JSON:");
    console.log(fixedProperJSON);
    
    try {
        const data = JSON.parse(fixedProperJSON);
        console.log("✓ Fixed JSON parses correctly!");
        console.log("Option value:", data.data.metadata.analysis_option);
    } catch (fixError) {
        console.log("✗ Fixed JSON still fails:", fixError.message);
    }
}

console.log("==============================================");
console.log("TESTS COMPLETED");
console.log("=============================================="); 