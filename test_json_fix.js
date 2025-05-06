// Test script for JSON repair with option field issues
console.log('Starting JSON repair test');

try {
    // Simple test first
    console.log('=== SIMPLE TEST ===');
    const simpleTest = '{"data":{"option":1,"value":2}}';
    console.log('Simple test JSON:', simpleTest);

    try {
        JSON.parse(simpleTest);
        console.log('UNEXPECTED: Simple test parsed without error');
    } catch (e) {
        console.log('Expected error on simple test:', e.message);
        
        // Try fixing
        const fixedSimple = simpleTest.replace(/"option"\s*:\s*(\d+)([,}])/g, '"option":"$1"$2');
        console.log('Fixed simple test:', fixedSimple);
        
        try {
            const parsedSimple = JSON.parse(fixedSimple);
            console.log('Simple test fixed successfully:', parsedSimple.data.option);
        } catch (e2) {
            console.log('Failed to fix simple test:', e2.message);
        }
    }

    // Create a problematic JSON string simulating our issue
    function createProblemJSON() {
        try {
            console.log('Creating test JSON string');
            // Create a shorter JSON string for testing
            let prefix = '{"status":"success","data":{"time_series":[';
            
            // Add data points to simulate our structure
            for (let i = 0; i < 5; i++) {
                prefix += `{"date":"2023-01-${(i % 30) + 1}","value":${Math.random() * 100}},`;
            }
            
            // Remove the trailing comma
            prefix = prefix.slice(0, -1);
            prefix += '],';
            
            // Add the problematic part - this is the key: extra quote after the number
            const problematic = '"option":1", "time_series_more"';
            
            // Add more content
            let suffix = ':[';
            suffix += `{"date":"2023-02-01","value":50}`;
            suffix += ']},"metadata":{"keyword":"test"}}';
            
            const result = prefix + problematic + suffix;
            console.log('Sample of broken JSON:', result);
            return result;
        } catch (e) {
            console.error('Error creating test JSON:', e);
            return '{"broken":"true"}';
        }
    }

    // Create simple broken JSON for testing
    const brokenJson = '{"data":{"option":1", "next_field":"value"}}';
    console.log('Simple broken JSON for testing:', brokenJson);
    
    try {
        JSON.parse(brokenJson);
        console.log('UNEXPECTED: Broken JSON parsed without error');
    } catch (e) {
        console.log('Expected parse error on broken JSON:', e.message);
        console.log('Attempting to fix broken JSON directly');
        
        try {
            // Apply direct fix
            const fixed = brokenJson.replace(/"option"\s*:\s*(\d+)"\s*,/g, '"option":"$1",');
            console.log('Fixed JSON:', fixed);
            
            const parsed = JSON.parse(fixed);
            console.log('Successfully fixed and parsed broken JSON');
        } catch (fixErr) {
            console.error('Failed to fix broken JSON:', fixErr);
        }
    }

    console.log('End of test');
} catch (globalError) {
    console.error('Global error in test:', globalError);
} 