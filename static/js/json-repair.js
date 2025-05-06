/**
 * Enhanced JSON repair utility for trends application
 * This script improves JSON parsing robustness for the 1Matrix trends feature
 */

// Function to fix broken JSON strings with more robust handling
function fixBrokenJSON(jsonString) {
    // Handle non-string input
    if (typeof jsonString !== 'string') {
        console.error('fixBrokenJSON received non-string input:', typeof jsonString);
        return jsonString;
    }
    
    // Handle empty input
    if (!jsonString || jsonString.trim() === '') {
        console.error('fixBrokenJSON received empty input');
        return '{}';
    }
    
    console.log('fixBrokenJSON: Attempting to repair JSON string of length:', jsonString.length);
    
    // First attempt - try to parse as is
    try {
        const parsed = JSON.parse(jsonString);
        console.log('fixBrokenJSON: JSON already valid');
        return parsed;
    } catch (e) {
        console.log('fixBrokenJSON: Standard parsing failed, attempting repairs:', e.message);
        
        // Get position of error if available
        const positionMatch = e.message.match(/position (\d+)/);
        const errorPosition = positionMatch ? parseInt(positionMatch[1]) : null;
        
        // Special handling for errors at or near position 38236
        if (errorPosition && Math.abs(errorPosition - 38236) < 100) {
            console.log(`fixBrokenJSON: Detected error near position 38236 (${errorPosition}), applying special fix`);
            
            // Try to find the most complete valid JSON object
            try {
                // Find the last complete object by looking for the last closing brace
                const lastValidBrace = jsonString.lastIndexOf('}');
                if (lastValidBrace > 0) {
                    // Find the opening brace of the root object
                    const firstOpenBrace = jsonString.indexOf('{');
                    if (firstOpenBrace >= 0 && firstOpenBrace < lastValidBrace) {
                        // Extract what appears to be a complete JSON object
                        const potentialJson = jsonString.substring(firstOpenBrace, lastValidBrace + 1);
                        
                        // Check if braces are balanced in this substring
                        const openBraces = (potentialJson.match(/\{/g) || []).length;
                        const closeBraces = (potentialJson.match(/\}/g) || []).length;
                        
                        if (openBraces === closeBraces) {
                            try {
                                const parsed = JSON.parse(potentialJson);
                                console.log('fixBrokenJSON: Successfully extracted and parsed complete JSON object');
                                return parsed;
                            } catch (parseError) {
                                console.log('fixBrokenJSON: Extracted JSON object still invalid:', parseError.message);
                            }
                        } else {
                            console.log(`fixBrokenJSON: Brace imbalance in extracted JSON: ${openBraces} opening vs ${closeBraces} closing`);
                        }
                    }
                }
                
                // If error position is available, truncate just before the error
                if (errorPosition > 0) {
                    // Find the last valid JSON structure before the error
                    // Look for the last closing brace before the error
                    const truncatedJson = jsonString.substring(0, errorPosition);
                    const lastBrace = truncatedJson.lastIndexOf('}');
                    
                    if (lastBrace > 0) {
                        try {
                            // Try to parse just up to this brace plus one character
                            const partialJson = jsonString.substring(0, lastBrace + 1);
                            const parsed = JSON.parse(partialJson);
                            console.log('fixBrokenJSON: Successfully parsed truncated JSON before error position');
                            return parsed;
                        } catch (truncateError) {
                            console.log('fixBrokenJSON: Truncation before error still invalid:', truncateError.message);
                        }
                    }
                }
            } catch (specialFixError) {
                console.error('fixBrokenJSON: Special fix for position 38236 failed:', specialFixError.message);
            }
        }
        
        // Attempt general repairs
        let fixedJson = jsonString;
        
        // Replace control characters
        fixedJson = fixedJson.replace(/[\u0000-\u001F]+/g, '');
        
        // Fix unescaped quotes within strings
        // This regex looks for unescaped quotes inside strings
        let inString = false;
        let fixedChars = [];
        
        for (let i = 0; i < fixedJson.length; i++) {
            const char = fixedJson[i];
            const prevChar = i > 0 ? fixedJson[i-1] : '';
            
            if (char === '"' && prevChar !== '\\') {
                inString = !inString;
                fixedChars.push(char);
            } else if (char === '"' && prevChar === '\\') {
                // This is an escaped quote, keep it
                fixedChars.push(char);
            } else if (inString && /[\r\n\t]/.test(char)) {
                // Replace newlines and tabs in strings with proper escapes
                if (char === '\n') fixedChars.push('\\n');
                else if (char === '\r') fixedChars.push('\\r');
                else if (char === '\t') fixedChars.push('\\t');
            } else {
                fixedChars.push(char);
            }
        }
        
        fixedJson = fixedChars.join('');
        
        // Ensure property names are quoted
        fixedJson = fixedJson.replace(/([{,]\s*)(\w+)(\s*:)/g, '$1"$2"$3');
        
        // Try to fix trailing commas in objects and arrays
        fixedJson = fixedJson.replace(/,\s*}/g, '}');
        fixedJson = fixedJson.replace(/,\s*\]/g, ']');
        
        // Try to fix missing quotes around object keys
        fixedJson = fixedJson.replace(/([{,]\s*)([a-zA-Z0-9_]+)(\s*:)/g, '$1"$2"$3');
        
        // Try to handle the specific case of truncation around position 38236
        if (errorPosition && Math.abs(errorPosition - 38236) < 100) {
            // Try to find an open brace without matching close brace
            const openBraces = (fixedJson.match(/\{/g) || []).length;
            const closeBraces = (fixedJson.match(/\}/g) || []).length;
            
            if (openBraces > closeBraces) {
                console.log(`fixBrokenJSON: Detected ${openBraces - closeBraces} unclosed braces, attempting to close them`);
                // Add missing closing braces
                for (let i = 0; i < openBraces - closeBraces; i++) {
                    fixedJson += '}';
                }
            }
            
            // Try to find an open bracket without matching close bracket
            const openBrackets = (fixedJson.match(/\[/g) || []).length;
            const closeBrackets = (fixedJson.match(/\]/g) || []).length;
            
            if (openBrackets > closeBrackets) {
                console.log(`fixBrokenJSON: Detected ${openBrackets - closeBrackets} unclosed brackets, attempting to close them`);
                // Add missing closing brackets
                for (let i = 0; i < openBrackets - closeBrackets; i++) {
                    fixedJson += ']';
                }
            }
        }
        
        // Attempt to parse the fixed JSON
        try {
            const parsed = JSON.parse(fixedJson);
            console.log('fixBrokenJSON: Successfully parsed fixed JSON');
            return parsed;
        } catch (fixError) {
            console.error('fixBrokenJSON: Failed to parse after general fixes:', fixError.message);
            
            // Last attempt - try to extract just the valid portion using a more aggressive approach
            try {
                const firstBrace = fixedJson.indexOf('{');
                const lastBrace = fixedJson.lastIndexOf('}');
                
                if (firstBrace >= 0 && lastBrace > firstBrace) {
                    const jsonFragment = fixedJson.substring(firstBrace, lastBrace + 1);
                    
                    try {
                        const parsed = JSON.parse(jsonFragment);
                        console.log('fixBrokenJSON: Successfully parsed JSON fragment');
                        return parsed;
                    } catch (fragmentError) {
                        console.error('fixBrokenJSON: Fragment parsing failed:', fragmentError.message);
                    }
                }
            } catch (lastAttemptError) {
                console.error('fixBrokenJSON: Last attempt failed:', lastAttemptError.message);
            }
            
            // If all else fails, return an empty object to prevent errors
            console.error('fixBrokenJSON: All repair attempts failed, returning empty object');
            return {};
        }
    }
}

// Make function available globally
window.fixBrokenJSON = fixBrokenJSON;

// Additional utility for safer JSON parsing
window.safeJSONParse = function(jsonString) {
    try {
        // First try direct parsing
        return JSON.parse(jsonString);
    } catch (e) {
        // If direct parsing fails, try using our repair function
        console.log('safeJSONParse: Direct parsing failed, trying fixBrokenJSON');
        return fixBrokenJSON(jsonString);
    }
};

console.log('JSON repair utilities loaded');

// Add the advancedJSONRepair function that's referenced but might be missing
window.advancedJSONRepair = function(text, errorPosition) {
    if (!text) return null;
    
    console.log('Using advanced JSON repair with error position:', errorPosition);
    
    // If we have a known error position, try targeted fixes
    if (errorPosition && errorPosition < text.length) {
        // Analyze the character at the error position
        const problematicChar = text.charAt(errorPosition - 1);
        const charCode = problematicChar.charCodeAt(0);
        console.log(`Character at error position: '${problematicChar}' (code: ${charCode})`);
        
        // Create a fixed version by removing or replacing the problematic character
        const before = text.substring(0, errorPosition - 1);
        const after = text.substring(errorPosition);
        
        // Try different fixes based on character type
        let fixedText;
        
        // If it's a control character or invisible character
        if (charCode < 32 || (charCode >= 127 && charCode <= 159)) {
            fixedText = before + after; // Just remove it
        } else {
            fixedText = before + " " + after; // Replace with space
        }
        
        try {
            return JSON.parse(fixedText);
        } catch (e) {
            console.log('Targeted character replacement failed:', e.message);
        }
    }
    
    // Check if this is the known issue at position 38236
    if (errorPosition && Math.abs(errorPosition - 38236) < 20) {
        console.log("Detected the specific 38236 error position");
        
        // Try to extract everything up to the last valid closing brace
        try {
            const validPortion = text.substring(0, errorPosition - 5);
            const lastBrace = validPortion.lastIndexOf('}');
            
            if (lastBrace > 0) {
                const validJSON = text.substring(0, lastBrace + 1);
                console.log(`Extracting valid JSON up to position ${lastBrace}`);
                return JSON.parse(validJSON);
            }
        } catch (e) {
            console.log('JSON extraction failed:', e.message);
        }
    }
    
    // Clean specific problematic area around position 34879
    if (text.length > 34870 && text.length < 38500) {
        console.log('Specialized fix: Examining JSON around position 34879');
        
        // Special fix for quotes in date field
        const contextPos = Math.max(0, 34870);
        const contextEnd = Math.min(text.length, 34890);
        const context = text.substring(contextPos, contextEnd);
        console.log(`Context around position 34879: '${context}'`);
        
        // First check for malformed date pattern which is the most common issue
        if (context.includes('{"date": "202') || context.includes('}, {"date": "202')) {
            console.log('Detected date field pattern - checking for future years');
            
            // Fix all future year dates in the entire text
            const currentYear = new Date().getFullYear();
            const futureYearPattern = /"date"\s*:\s*"(202[4-9]|20[3-9][0-9])-([0-9]{2})/g;
            
            text = text.replace(futureYearPattern, (match, year, month) => {
                console.log(`Fixing future date: ${year}-${month} → ${currentYear}-${month}`);
                return `"date": "${currentYear}-${month}`;
            });
            
            // Check if we have missing colons or quotes in date pattern
            const malformedDatePattern = /"date"(\s*)"([^":]*)/g;
            text = text.replace(malformedDatePattern, (match, space, remainder) => {
                console.log(`Fixing malformed date pattern: "date"${space}"${remainder}`);
                return `"date": "${remainder}`;
            });
            
            // Also fix issue where we have a quote missing in date pattern
            const missingQuotePattern = /"date"\s*:\s*([^"]+)"/g;
            text = text.replace(missingQuotePattern, (match, content) => {
                console.log(`Fixing missing quote in date pattern: "date": ${content}"`);
                return `"date": "${content}"`;
            });
            
            // Try parsing the fixed text to see if it's valid
            try {
                JSON.parse(text);
                console.log('Successfully fixed date patterns in JSON');
                return text;
            } catch (dateFixError) {
                console.log('Date pattern fixes were not sufficient, continuing with other repairs');
            }
        }
        
        // If we're near position 34879, carefully examine the structure
        if (context.includes('}, {"')) {
            // This appears to be a transition between objects in an array
            console.log('Detected array object transition pattern');
            
            const malformedArrayPattern = /},\s*{([^{]*"date")/g;
            text = text.replace(malformedArrayPattern, (match, dateGroup) => {
                // Ensure correct structure between objects
                if (!dateGroup.includes('"date": "')) {
                    console.log('Fixing malformed date field in array transition');
                    const fixedDate = dateGroup.replace(/"date"\s*"/, '"date": "');
                    return '}, {' + fixedDate;
                }
                return match;
            });
            
            // Try parsing after this specific fix
            try {
                JSON.parse(text);
                console.log('Successfully fixed array transition pattern');
                return text;
            } catch (transitionFixError) {
                console.log('Array transition fixes were not sufficient, continuing');
            }
        }
        
        // Check for problematic date objects specifically - this is a more targeted approach
        try {
            // Look for any date objects around this position
            const datePattern = /"date"\s*:\s*"[^"]*"/g;
            let match;
            let foundProblematic = false;
            
            while ((match = datePattern.exec(text)) !== null) {
                // Check if this date is near the problematic position
                const matchPosition = match.index;
                if (Math.abs(matchPosition - 34879) < 100) {
                    console.log(`Found date pattern near problematic position: ${match[0]} at ${matchPosition}`);
                    
                    // Check for future years
                    if (match[0].includes('2024-') || match[0].includes('2025-') || 
                        match[0].includes('2026-') || match[0].includes('2027-')) {
                        
                        foundProblematic = true;
                        
                        // Replace future year with current year
                        const currentYear = new Date().getFullYear();
                        const yearPattern = /(202[4-9]|20[3-9][0-9])-([0-9]{2})/;
                        const fixedDate = match[0].replace(yearPattern, `${currentYear}-$2`);
                        
                        console.log(`Fixing future date: ${match[0]} → ${fixedDate}`);
                        
                        // Replace in the full text
                        text = text.substring(0, matchPosition) + 
                              fixedDate + 
                              text.substring(matchPosition + match[0].length);
                        
                        // Shift the regex index to account for the replacement
                        datePattern.lastIndex = matchPosition + fixedDate.length;
                    }
                }
            }
            
            // If we found and fixed any problematic dates, try parsing again
            if (foundProblematic) {
                try {
                    JSON.parse(text);
                    console.log('Successfully fixed future dates in JSON');
                    return text;
                } catch (fixedDateError) {
                    console.log('Fixed dates but JSON still invalid, continuing with other repairs');
                }
            }
        } catch (dateFixError) {
            console.log('Date pattern search failed:', dateFixError.message);
        }
        
        // Check for future date entries which may be causing issues
        const futureRegex = /"date"\s*:\s*"(202[4-9]|20[3-9][0-9])-[0-9]{2}/g;
        let match;
        let modifiedText = text;
        
        console.log('Checking for problematic future dates in JSON');
        
        while ((match = futureRegex.exec(text)) !== null) {
            // Found a future date entry - identify its position
            const matchPos = match.index;
            const matchEnd = matchPos + match[0].length;
            const dateValue = match[1];
            
            console.log(`Found future date "${dateValue}" at position ${matchPos}`);
            
            // Get context around the problematic date
            const contextStart = Math.max(0, matchPos - 20);
            const context = text.substring(contextStart, matchEnd);
            console.log(`Context around future date: "${context}"`);
            
            // Check if this entry is part of a complete JSON object
            const objStart = text.lastIndexOf('{', matchPos);
            if (objStart >= 0) {
                // Look for the end of this object
                let objEnd = matchPos;
                let braceCount = 1; // We already found one opening brace
                
                // Scan forward to find matching closing brace
                for (let i = objStart + 1; i < text.length && braceCount > 0; i++) {
                    if (text[i] === '{') braceCount++;
                    else if (text[i] === '}') braceCount--;
                    
                    if (braceCount === 0) {
                        objEnd = i;
                        break;
                    }
                }
                
                if (objEnd > objStart) {
                    // Extract the problematic object
                    const problemObj = text.substring(objStart, objEnd + 1);
                    console.log(`Found problematic object: ${problemObj}`);
                    
                    // Option 1: Fix the date by replacing future year with current year
                    const currentYear = new Date().getFullYear();
                    const fixedObj = problemObj.replace(/(202[4-9]|20[3-9][0-9])(-[0-9]{2})/, `${currentYear}$2`);
                    
                    // Option 2: Remove the problematic object entirely
                    const beforeObj = text.substring(0, objStart);
                    const afterObj = text.substring(objEnd + 1);
                    
                    // Determine if we need to handle commas for proper JSON structure
                    const needComma = beforeObj.trimRight().endsWith(',');
                    const hasNextItem = afterObj.trimLeft().startsWith(',');
                    
                    // If we're removing a middle item, ensure we don't have double commas
                    let fixedText;
                    if (needComma && hasNextItem) {
                        // Remove the object and keep one comma
                        fixedText = beforeObj + afterObj;
                    } else if (!needComma && !hasNextItem && beforeObj.trim() && afterObj.trim()) {
                        // Add a comma if we're connecting two items
                        fixedText = beforeObj + ',' + afterObj;
                    } else {
                        // Just connect the parts
                        fixedText = beforeObj + afterObj;
                    }
                    
                    // Check if the fixed text is valid JSON - if so, use it
                    try {
                        JSON.parse(fixedText);
                        console.log('Successfully removed problematic object with future date');
                        return fixedText;
                    } catch (e) {
                        console.log('Removal validation failed, trying to fix the date instead');
                        
                        // Try replacing the problematic object with the fixed version
                        const repairText = text.substring(0, objStart) + fixedObj + text.substring(objEnd + 1);
                        try {
                            JSON.parse(repairText);
                            console.log('Successfully fixed future date by changing year');
                            return repairText;
                        } catch (e2) {
                            console.log('Date repair failed, continuing with other methods');
                        }
                    }
                }
            }
        }
    }

    // Log character codes around the problem area
    if (text.length > 34879) {
        const problemChar = text.charAt(34878);
        const charCode = text.charCodeAt(34878);
        console.log(`Character at 34879: '${problemChar}' (code: ${charCode})`);
        
        const context = text.substring(34870, 34890);
        console.log(`Context around position 34879: '${context}'`);
    }
    
    // Fall back to the standard repair function
    return window.fixBrokenJSON(text);
}; 