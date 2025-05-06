// Comprehensive test for JSON repair function
console.log('==============================================');
console.log('STARTING COMPREHENSIVE JSON REPAIR TEST');
console.log('==============================================');

// Include the fixBrokenJSON function
function fixBrokenJSON(text) {
    console.log('Attempting to fix JSON data of length:', text.length);
    
    // Special handling for option field issues (most common issue)
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
        .replace(/"option"\s*:\s*(\d+)([,}])/g, '"option":"$1"$2')
        .replace(/"option"\s*:\s*(\d+)"\s*,/g, '"option":"$1",');
    
    // Return the cleaned text
    return cleanText;
}

// Test cases - different ways the "option" field might be broken
const testCases = [
    {
        name: "Correct JSON with option as number",
        json: '{"option":1,"field":"value"}',
        shouldPass: true
    },
    {
        name: "Option with extra quote after number",
        json: '{"option":1","field":"value"}',
        shouldPass: false
    },
    {
        name: "Option with number but no quotes",
        json: '{"option":1,"field":"value"}',
        shouldPass: true
    },
    {
        name: "Option with quotes only on one side",
        json: '{"option":"1,"field":"value"}',
        shouldPass: false
    },
    {
        name: "Option with weird whitespace",
        json: '{"option" : 1, "field":"value"}',
        shouldPass: true
    },
    {
        name: "Multiple option fields",
        json: '{"data":{"option":1},"metadata":{"option":2}}',
        shouldPass: true
    },
    {
        name: "Trailing comma in object",
        json: '{"option":1,"field":"value",}',
        shouldPass: false
    }
];

// Force to console
console.log("===============================================");
console.log("Test cases to run:", testCases.length);
console.log("===============================================");

// Run each test
let passCount = 0;
let fixCount = 0;

testCases.forEach((test, index) => {
    console.log(`\n----------------------------------------------`);
    console.log(`TEST ${index + 1}: ${test.name}`);
    console.log(`Original: ${test.json}`);
    
    // Try to parse the original
    let originalParsed = false;
    try {
        const result = JSON.parse(test.json);
        originalParsed = true;
        console.log(`✓ Original parses fine: ${JSON.stringify(result)}`);
        
        // Check if option field exists and show its value
        if (result.option !== undefined) {
            console.log(`Option value: ${result.option} (type: ${typeof result.option})`);
        }
    } catch (e) {
        console.log(`✗ Original fails parsing: ${e.message}`);
    }
    
    // Apply fix if original didn't parse or we want to check the fix anyway
    if (!originalParsed || !test.shouldPass) {
        const fixed = fixBrokenJSON(test.json);
        console.log(`After fix: ${fixed}`);
        
        try {
            const result = JSON.parse(fixed);
            console.log(`✓ Fixed JSON parses correctly: ${JSON.stringify(result)}`);
            
            // Check if option field exists and show its value
            if (result.option !== undefined) {
                console.log(`Option value: ${result.option} (type: ${typeof result.option})`);
            }
            
            if (!originalParsed) {
                fixCount++;
            }
            passCount++;
        } catch (e) {
            console.log(`✗ Fixed JSON still fails: ${e.message}`);
        }
    } else {
        passCount++;
    }
});

console.log("\n===============================================");
console.log(`TEST SUMMARY: ${passCount}/${testCases.length} tests passed`);
if (fixCount > 0) {
    console.log(`${fixCount} broken JSONs were successfully fixed`);
}
console.log("===============================================");
console.log("COMPREHENSIVE TEST COMPLETED");
console.log("==============================================="); 