// Minimal test case for JSON repair
console.log("Starting basic test");

// Test case 1: Simple unquoted option field
const test1 = '{"option":1,"field":"value"}';
console.log("Test 1 original:", test1);

try {
    const parsed1 = JSON.parse(test1);
    console.log("Test 1 parsed successfully:", parsed1.option);
} catch (e) {
    console.error("Test 1 failed to parse:", e.message);
}

// Test case 2: Broken option field with extra quote
const test2 = '{"option":1", "field":"value"}';  
console.log("Test 2 original:", test2);

try {
    const parsed2 = JSON.parse(test2);
    console.log("Test 2 parsed successfully - unexpected!");
} catch (e) {
    console.log("Test 2 failed to parse (expected):", e.message);
    
    // Fix using regex
    const fixed2 = test2.replace(/"option"\s*:\s*(\d+)"\s*,/g, '"option":"$1",');
    console.log("Test 2 fixed:", fixed2);
    
    try {
        const parsedFixed2 = JSON.parse(fixed2);
        console.log("Test 2 fixed and parsed successfully:", parsedFixed2.option);
    } catch (e2) {
        console.error("Test 2 could not be fixed:", e2.message);
    }
}

console.log("Test completed"); 